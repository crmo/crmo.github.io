---
title: "iOS用原生代码读写Webview的Local Storage"
date: 2018-04-03T00:00:00+08:00
lastmod: 2018-10-07T08:13:38.000Z
url: "/2018/04/03/iOS用原生代码读写Webview的Local Storage/"
tags:
  - "iOS知识小结"
draft: false
---

## 背景

公司项目使用的`Cordova`混合开发的，有一个模块以前用H5实现的，新版本用原生来实现，于是需要迁移数据。H5使用的Local Storage存的数据，原生要拿到数据有两种方案：
1. 用`WebView`执行js方法来读取数据；
2. 找到`Local Storage`存储路径，直接读取；

方案一实现起来比较简单，但是会存在一些问题，需要多开一个Webview来迁移数据，而且这个过程不好控制，不是最优解，本文讨论的是方案二。

## 直接读写Local Storage

先说结论，`Local Storage`的其实是一个Sqlite数据库，我们要读写数据只要找到这个数据库，然后就可以实现手动读写了。

### 数据库存放路径

>iOS 5.1及之前使用UIWebView：Library/Caches/
iOS 5.1之后使用UIWebView：Library/WebKit/LocalStorage/
WKWebView：Library/WebKit/WebsiteData/LocalStorage/

> // UIWebView可以从UserDefault取出LocalStorage的路径
> [[NSUserDefaults standardUserDefaults] objectForKey:@"WebKitLocalStorageDatabasePathPreferenceKey"]

![](15226716925888.jpg)

### 数据存储方式

数据存在`ItemTable`表，只有`key`和`value`两个字段，key直接用NSString可以取出来，value取出来是一个NSData，需要用`NSUTF16LittleEndianStringEncoding`解码。

![](15226719772136.jpg)

### 读写数据

写了个简易的Demo，用的[FMDB](https://github.com/ccgus/fmdb)来操作数据库，这里就不介绍了。

```
// 取数据
- (NSString *)valueWithKey:(NSString *)key {
    if ([NSString isNull:key]) {
        return nil;
    }
    
    __block NSString *result;
    [self.dataQueue inDatabase:^(FMDatabase *db) {
        NSData *data = [db dataForQuery:@"select value from ItemTable where key = ?", key];
        result = [[NSString alloc] initWithData:data encoding:NSUTF16LittleEndianStringEncoding];
    }];
    return result;
}
    
```

```
// 存数据
- (BOOL)saveValue:(NSString *)value forKey:(NSString *)key {
    if ([NSString isNull:value] ||
        [NSString isNull:key]) {
        return NO;
    }
    
    __block BOOL result;
    [self.dataQueue inDatabase:^(FMDatabase *db) {
        [db executeUpdate:@"delete from ItemTable where key = ?", key];
        NSData *data = [value dataUsingEncoding:NSUTF16LittleEndianStringEncoding];
        result = [db executeUpdate:@"insert into ItemTable (key, value) values (?, ?)", key, data];
    }];
    return result;
}
```

## WebKit源码分析

为了找到`Local Storage`存放的路径，在网上找了很多资料，发现这方面的资料很少，也没有怕出现各种坑或者系统版本兼容，于是决定研究下WebKit源码，从源码里面找答案。

Webkit、WebCore[源码地址](https://opensource.apple.com/release/ios-110.html)。可以看到WebKit有两个版本，`WebKit-7604.1.38.0.7`和`WebKit2-7604.1.38.0.7`，前者是UIWebView的，后者是WKWebView的。

![](15226724314772.jpg)


解压`WebKit-7604.1.38.0.7`。用Xcode打开工程文件，工程名叫`WebKitLegacy`，这个命名太形象了，WebKit的遗产。苦于各种历史原因，公司项目还停留在UIWebView的阶段，心塞。
在WebStorageManager.m类中可以看到关于`Local Storage`保存路径的定义，路径是`Library/WebKit/LocalStorage/`。

```
static void initializeLocalStoragePath()
{
    NSUserDefaults *defaults = [NSUserDefaults standardUserDefaults];
    sLocalStoragePath = [defaults objectForKey:WebStorageDirectoryDefaultsKey];
    if (!sLocalStoragePath || ![sLocalStoragePath isKindOfClass:[NSString class]]) {
        NSArray *paths = NSSearchPathForDirectoriesInDomains(NSLibraryDirectory, NSUserDomainMask, YES);
        NSString *libraryDirectory = [paths objectAtIndex:0];
        sLocalStoragePath = [libraryDirectory stringByAppendingPathComponent:@"WebKit/LocalStorage"];
    }
    sLocalStoragePath = [[sLocalStoragePath stringByStandardizingPath] retain];
}
```

解压`WebKit2-7604.1.38.0.7`，路径定义在`WKProcessPool.mm`类中，路径是`Library/WebKit/WebsiteData/LocalStorage/`。

```
+ (NSURL *)_websiteDataURLForContainerWithURL:(NSURL *)containerURL bundleIdentifierIfNotInContainer:(NSString *)bundleIdentifier
{
    NSURL *url = [containerURL URLByAppendingPathComponent:@"Library" isDirectory:YES];
    url = [url URLByAppendingPathComponent:@"WebKit" isDirectory:YES];

    if (!WebKit::processHasContainer() && bundleIdentifier)
        url = [url URLByAppendingPathComponent:bundleIdentifier isDirectory:YES];

    return [url URLByAppendingPathComponent:@"WebsiteData" isDirectory:YES];

```

至此关于`UIWebView`和`WKWebView`的存放路径我们已经能够确定了，那么文件名是怎么定义的呢，这要看`WebCore`的源码了，在`SecurityOriginData.cpp`中定义了文件名命名规则。

```
String SecurityOriginData::databaseIdentifier() const
{
    // Historically, we've used the following (somewhat non-sensical) string
    // for the databaseIdentifier of local files. We used to compute this
    // string because of a bug in how we handled the scheme for file URLs.
    // Now that we've fixed that bug, we still need to produce this string
    // to avoid breaking existing persistent state.
    if (equalIgnoringASCIICase(protocol, "file"))
        return ASCIILiteral("file__0");
    
    StringBuilder stringBuilder;
    stringBuilder.append(protocol);
    stringBuilder.append(separatorCharacter);
    stringBuilder.append(encodeForFileName(host));
    stringBuilder.append(separatorCharacter);
    stringBuilder.appendNumber(port.value_or(0));
    
    return stringBuilder.toString();
}
```

从上面代码我们可以得出结论，如果是file协议的url，文件名定义为`file__0`，否则会根据它的url来生成一个文件名。

在跟代码的时候，发现`UIWebView`会把`Local Storage`的存储路径存在`UserDefault`里，存储的Key是`WebKitLocalStorageDatabasePathPreferenceKey`（定义在`WebPreferenceKeysPrivate.h`）。在文件`WebPrefences.mm`中可以找到相关代码

```
- (NSString *)_localStorageDatabasePath
{
    return [[self _stringValueForKey:WebKitLocalStorageDatabasePathPreferenceKey] stringByStandardizingPath];
}


- (NSString *)_stringValueForKey:(NSString *)key
{
    id s = [self _valueForKey:key];
    return [s isKindOfClass:[NSString class]] ? (NSString *)s : nil;
}

- (id)_valueForKey:(NSString *)key
{
    NSString *_key = KEY(key);
#if PLATFORM(IOS)
    __block id o = nil;
    dispatch_sync(_private->readWriteQueue, ^{
        o = [_private->values.get() objectForKey:_key];
    });
#else
    id o = [_private->values.get() objectForKey:_key];
#endif
    if (o)
        return o;
    o = [[NSUserDefaults standardUserDefaults] objectForKey:_key];
    if (!o && key != _key)
        o = [[NSUserDefaults standardUserDefaults] objectForKey:key];
    return o;
}
```

## Local Storage存在的问题

在查询资料的过程中，发现了很多Local Storage的缺陷，有一篇关于Local Storage的[论文](https://thinkmind.org/download.php?articleid=mobility_2017_2_10_90007)可以参考。有以下几点：
1. 不要用Local Storage来做持久化存储，在iOS中，出现存储空间紧张时，它会被系统清理掉；
2. 不要用Local Storage来存大数据，它的读写效率很低下，因为它需要序列化/反序列化
3. 它有5M的大小限制

总结起来就一句话，不要滥用Local Storage。有很多替代方案，比如https://github.com/TheCocoaProject/cordova-plugin-nativestorage



## 参考资料

https://github.com/wootwoot1234/react-native-webkit-localstorage-reader/issues/4
https://blog.csdn.net/shuimuniao/article/details/8027276
https://stackoverflow.com/questions/26465409/restore-localstorage-data-from-old-cordova-app/49604587#49604587
https://stackoverflow.com/questions/9067249/how-do-i-access-html5-local-storage-created-by-phonegap-on-ios/49604541#49604541
https://issues.apache.org/jira/browse/CB-12509


