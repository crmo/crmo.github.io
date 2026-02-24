---
title: "iOS的Cookie管理"
date: 2018-03-01T20:00:00+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2018/03/01/iOS的Cookie管理/"
tags:
  - "iOS知识小结"
draft: false
---

![photo-1490633874781-1c63cc424610](photo-1490633874781-1c63cc424610.jpeg)

## 背景


最近有一个需求，需要手动的去缓存cookie，然后启动APP的时候设置缓存过的cookie，项目网络框架用的是Afnetworking。

## 解决方案

翻了下Afnetworking的issue，发现了作者对于cookie的解释

> Afnetworking没有对Cookie做过处理

![](15197156684835.jpg)

使用`NSHTTPCookieStorage`即可实现cookie的管理。上代码！

**存cookie**

```
NSArray *cookies = [[NSHTTPCookieStorage sharedHTTPCookieStorage] cookiesForURL:[NSURL URLWithString:url]];
NSData *data = [NSKeyedArchiver archivedDataWithRootObject:cookies];
NSUserDefaults *userDefaults = [NSUserDefaults standardUserDefaults];
[userDefaults setObject:data forKey:@"cookie"];
```

**设置cookie**

```
NSData *cookiesdata = [[NSUserDefaults standardUserDefaults] objectForKey:@"m3cookie"];
    if([cookiesdata length]) {
        NSArray *cookies = [NSKeyedUnarchiver unarchiveObjectWithData:cookiesdata];
        NSHTTPCookie *cookie;
        for (cookie in cookies) {
            [[NSHTTPCookieStorage sharedHTTPCookieStorage] setCookie:cookie];
        }
    }
```

**清理cookie**

```
NSHTTPCookie *cookie;
NSHTTPCookieStorage *storage = [NSHTTPCookieStorage sharedHTTPCookieStorage];
for (cookie in [storage cookies]) {
    [storage deleteCookie:cookie];
}
```
---

参考文章：
> [NSHTTPCookieStorage官方文档](https://developer.apple.com/documentation/foundation/nshttpcookiestorage)
> [Persisting Cookies In An iOS Application?](https://stackoverflow.com/questions/4597763/persisting-cookies-in-an-ios-application/8713316#8713316)
> [Clear cookies for response in AFNetworking 2
](https://stackoverflow.com/questions/21625313/clear-cookies-for-response-in-afnetworking-2)

