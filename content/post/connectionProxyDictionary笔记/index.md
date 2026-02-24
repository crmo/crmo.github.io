---
title: "connectionProxyDictionary 笔记"
description: "记录 NSURLSessionConfiguration 的 connectionProxyDictionary 属性用法，介绍如何编程设置 HTTP/HTTPS 网络代理以及通过设置空字典禁止抓包工具拦截的技巧。"
date: 2019-06-16T00:00:00+08:00
lastmod: 2019-06-16T03:53:17.000Z
url: "/2019/06/16/connectionProxyDictionary笔记/"
tags:
  - "iOS知识小结"
draft: false
---

最近研究了下 `connectionProxyDictionary`，做一个简单的笔记。[官方文档](https://developer.apple.com/documentation/foundation/nsurlsessionconfiguration/1411499-connectionproxydictionary)是这么描述的。

> This property controls which proxy tasks within sessions based on this configuration use when connecting to remote hosts.
The default value is NULL, which means that tasks use the default system settings.

这个属性可以设置网络代理，默认值是 NULL，使用系统的代理设置。

> 有一个比较巧妙的用法，可以通过设置为空字典可以禁止代理抓包(charles、fiddler等)。

上代码。

```objc
NSString* proxyHost =  @"192.168.12.23";//@"myProxyHost.com";
NSNumber* proxyPort = [NSNumber numberWithInt: 12345];


// 创建一个代理服务器，包括HTTP或HTTPS代理，当然还可以添加SOCKS,FTP,RTSP等
NSDictionary *proxyDict = @{
    (NSString *)kCFNetworkProxiesHTTPEnable  : [NSNumber numberWithInt:1],
    (NSString *)kCFNetworkProxiesHTTPProxy: proxyHost,
    (NSString *)kCFNetworkProxiesHTTPProxyPort: proxyPort,

    (NSString *)kCFNetworkProxiesHTTPSEnable : [NSNumber numberWithInt:1],
    (NSString *)kCFNetworkProxiesHTTPSProxy: proxyHost,
    (NSString *)kCFNetworkProxiesHTTPSProxyPort: proxyPort,
};

NSURLSessionConfiguration *configuration = [NSURLSessionConfiguration ephemeralSessionConfiguration];
// 设置代理
configuration.connectionProxyDictionary = proxyDict;

// 禁止代理
configuration.connectionProxyDictionary = @{};
```

## 参考资料

1、[Apple 文档](https://developer.apple.com/documentation/foundation/nsurlsessionconfiguration/1411499-connectionproxydictionary)
2、[How to programmatically add a proxy to an NSURLSession](https://stackoverflow.com/questions/28101582/how-to-programmatically-add-a-proxy-to-an-nsurlsession)