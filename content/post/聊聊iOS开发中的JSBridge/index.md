---
title: "聊聊iOS开发中的JSBridge"
date: 2018-10-22T00:00:00+08:00
lastmod: 2018-10-22T13:40:18.000Z
url: "/2018/10/22/聊聊iOS开发中的JSBridge/"
tags:
  - "iOS知识小结"
draft: false
---

> 2018.10.22

![tower-bridge-2324875_1280](tower-bridge-2324875_1280.jpg)

## 前言

Hybrid App（混合模式移动应用）是指介于web-app、native-app这两者之间的app，兼具“Native App良好用户交互体验的优势”和“Web App跨平台开发的优势”。谈到Hybrid App，JS与Native code的交互就是一个绕不开的话题，这时就需要“一座桥”来连接两端。
`JSBridge`架起了一座连接`JavaScript`与`Native Code`的桥梁，让两端可以相互调用。

![JSBridge](JSBridge.png)

本文基于`UIWebView`，将会分别介绍3种方案。通过`Iframe`、`Ajax`、`JSCore`来实现JSBridge，涉及到的[Demo地址](https://github.com/crmo/CRJSBridgeDemo)，顺手给个Star呗😏。

## 实现方案

### Iframe

废话不多说，直入主题，首先讲的这种方案比较常见。`WebViewJavascriptBridge`与`Cordava`都是采用的该方案（推荐看看我之前的文章[Cordova源码解析](http://crmo.github.io/2018/05/09/Cordova源码解析/)）。
核心思路就是在UIWebView拦截Iframe的src，双方提前约定好协议，例如`https://__jsbridge__`就是一次调用开始。
可以学习`Cordova`的策略，将并发的多次调用打包合并为一次处理，可以优化性能。

#### 实现

1.JS暴露一个方法给Native，接收执行结果

```js
function responseFromObjC(response) {
    if (!callback) {
        return;
    }
    callback(response);
}
```

2.Native实现`UIWebView`的代理，在`webView:shouldStartLoadWithRequest:navigationType:`方法拦截请求，识别到特定URL，开始一次调用流程。

```objectivec
// 拦截JS调用原生核心方法
- (BOOL)webView:(UIWebView *)webView shouldStartLoadWithRequest:(NSURLRequest *)request navigationType:(UIWebViewNavigationType)navigationType {
    NSURL *url = request.URL;
    // 判断url是否是JSBridge调用
    if ([url.host isEqualToString:@"__jsbridge__"]) {
       // 处理JS调用Native
        return NO;
    }
    return YES;
}
```

3.JS开启一个Iframe，加载一个特定的URL，开始一次调用

```js
var iframe = document.createElement('iframe');
iframe.style.display = 'none';
iframe.src = 'https://__jsbridge__?action='+ action + '&data=' + data;
document.documentElement.appendChild(iframe);
```

4.Native方法执行完成后，调用JS方法`responseFromObjC`将结果回传给JS。

```objectivec
...
// 获取调用参数，demo的调用方式是：'https://__jsbridge__?action=action&data='
// 参数直接放在query里面的，更好的方案是js暴露一个方法给原生，原生调用方法获取数据
NSURLComponents *urlComponents = [NSURLComponents componentsWithURL:url resolvingAgainstBaseURL:YES];
NSArray *queryItems = urlComponents.queryItems;
NSMutableDictionary *params = [NSMutableDictionary dictionary];
for (NSURLQueryItem *queryItem in queryItems) {
    NSString *key = queryItem.name;
    NSString *value = queryItem.value;
    [params setObject:value forKey:key];
}
NSString *action = params[@"action"];
NSString *data = params[@"data"];

if ([action isEqualToString:@"alertMessage"]) {
    // 调用原生方法，获取数据
    // js暴露方法`responseFromObjC`给原生，原生通过该方法回调
    // 在实际项目中，为了实现实现js并发原生方法，最好带一个callBackID，来区分不同的调用
    [webView stringByEvaluatingJavaScriptFromString:[NSString stringWithFormat:@"responseFromObjC('%@')", data]];
} else {
    [webView stringByEvaluatingJavaScriptFromString:[NSString stringWithFormat:@"responseFromObjC('Unkown action'"]];
}
```

PS:demo代码为了简化，直接将参数放在URL的query里，如果只传输一些简单数据是没有问题的，更好的方案是JS先将参数存放起来，通过URL传递一个key给Native，再暴露一个通过key取数据的方法，Native主动调用这个方法取。

### Ajax

第二种方案是JS使用`XMLHttpRequest`发起请求，在Native拦截达到调用的目的。通过自定义`NSURLProtocol`可以拦截到Ajax请求。Demo里有详细的代码和注释，建议结合Demo一起看。

#### 实现

1.新建类继承自`NSURLProtocol`，并注册。

```objectivec
[NSURLProtocol registerClass:[CRURLProtocol class]];
```

2.实现自定义`NSURLProtocol`，在`startLoading`方法拦截Ajax请求

```objectivec
- (void)startLoading {
    NSURL *url = [[self request] URL];
    // 拦截“http://__jsbridge__”请求
    if ([url.host isEqualToString:@"__jsbridge__"]) {
       // 处理JS调用Native
    }
}
```

3.JS发起Ajax请求，URL为提前约定的特殊值，例如：http://__jsbridge__。请求参数放在`Request Body`里。

```js
// 调用原生
function callNative(action, data) {
        var xhr = new window.XMLHttpRequest(),
        url = 'http://__jsbridge__';
        xhr.open('POST', url, false);
        xhr.send(JSON.stringify({
                    action: action,
                    data: data
                    }));
        return xhr.responseText;
}
```

4.Naive拦截到请求，获取参数，执行Native方法，最后通过Ajax的`Response`把结果返回给JS。

```objectivec
...
// 2. 从HTTPBody中取出调用参数
NSDictionary *dic = [NSJSONSerialization JSONObjectWithData:self.request.HTTPBody options:NSJSONReadingAllowFragments error:nil];
NSString *action = dic[@"action"];
NSString *data = dic[@"data"];
NSData *responseData;

// 3. 根据action转发到不同方法处理，param携带参数
if ([action isEqualToString:@"alertMessage"]) {
    responseData = [data dataUsingEncoding:NSUTF8StringEncoding];
} else {
    responseData = [@"Unknown action" dataUsingEncoding:NSUTF8StringEncoding];
}

// 4. 处理完成，将结果返回给js
[self sendResponseWithResponseCode:200 data:responseData mimeType:@"text/html"];
...

- (void)sendResponseWithResponseCode:(NSInteger)statusCode data:(NSData*)data mimeType:(NSString*)mimeType {
    NSHTTPURLResponse* response = [[NSHTTPURLResponse alloc] initWithURL:[[self request] URL] statusCode:statusCode HTTPVersion:@"HTTP/1.1" headerFields:@{@"Content-Type" : mimeType}];
    
    [[self client] URLProtocol:self didReceiveResponse:response cacheStoragePolicy:NSURLCacheStorageNotAllowed];
    if (data != nil) {
        [[self client] URLProtocol:self didLoadData:data];
    }
    [[self client] URLProtocolDidFinishLoading:self];
}
```

### JSCore

前两种方案虽然实现方法不一致，但是思路都是类似的，由于JS不能直接调用Native方法，通过曲线救国的方式，找到一个载体来传递信息。
第三种方案就比较直接了，使用iOS7推出的黑科技`JavaScriptCore`，将Native方法直接暴露给JS，打通两端的数据通道。谈到`JavaScriptCore`不得不说的是bang590的`JSPatch`，还有ReactNative、Weex等都是利用`JavaScriptCore`来实现各种炫酷的功能。(强力推荐一本Lefe_x的书[《一份走心的JS-Native交互电子书》](https://github.com/awesome-tips/iOS-Tips/blob/master/resources/一份走心的JS-Native交互电子书.pdf)，非常精彩)。
不过这种方案有个缺陷，`UIWebView`没有暴露`JSContext`，虽然可以通过KVC拿到，但是毕竟不是一种完美的解决方案，不知道上架会不会有风险（求知道的同学指教一下）。

#### 实现

实现流程就不细说了，流程比较简单，Demo里面有。说说关键实现代码

```objectivec
- (void)injectJSBridge {
    // 获取JSContext
    JSContext *context = [_webView valueForKeyPath:@"documentView.webView.mainFrame.javaScriptContext"];
    // 给JS注入方法callNative
    context[@"callNative"] = ^(JSValue *action, JSValue *data) {
        NSString *actionStr = [action toString];
        NSString *dataStr = [data toString];
        if ([actionStr isEqualToString:@"alertMessage"]) {
            return dataStr;
        } else {
            return @"Unkown action";
        }
    };
}
```

JS调用非常简单，一句话搞定。

```js
callNative("alertMessage", "Hello world!")
```

## 性能对比

为了验证三种方案的性能，设计了个简单的实验，分别执行了100、1000、10000次调用，测试手机iPhone X，系统iOS 12，时间对比如下图所示。
先说结论，JSCore的性能是最优的，`JSCore>Ajax>Iframe`。在低并发的时候三种方案差距不大，执行次数10000次时Iframe效率就很低了，Ajax次之，JSCore性能很稳定。当然实际使用的时候不会出现调用10000次这种极限情况。
`Cordova`对于并发有个优化策略，很值得参考，将并发的多次调用打包合并为一次处理。

![](15401284999756.jpg)
