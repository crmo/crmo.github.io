---
title: "Cordova源码解析（二）- 自定义UserAgent"
description: "解析 Cordova 中 CDVUserAgentUtil 的加锁机制，分析多 WebView 环境下通过 NSUserDefaults 设置 UserAgent 时如何避免数据竞争，详解锁的获取、释放流程。"
date: 2018-05-15T00:00:00+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2018/05/15/Cordova源码解析（二）- 自定义UserAgent/"
tags:
  - "源码学习"
draft: false
---

`UIWebView`没有提供设置UserAgent的接口，但是有一个办法可以间接的设置。

```
NSDictionary* dict = [[NSDictionary alloc] initWithObjectsAndKeys:value, @"UserAgent", nil];
[[NSUserDefaults standardUserDefaults] registerDefaults:dict];
```

通过设置`NSUserDefaults`中`UserAgent`的值来修改，但是这种设置方法有一个限制，需要在`UIWebView`的`loadRequest`之前调用才能生效(加载PDF比较特殊)。这是Cordova源码中关于这个问题的描述

> Setting the UserAgent must occur before a UIWebView is instantiated.
It is read per instantiation, so it does not affect previously created views.
Except! When a PDF is loaded, all currently active UIWebViews reload their
User-Agent from the NSUserDefaults some time after the DidFinishLoad of the PDF bah!

## CDVUserAgentUtil

在多WebView的情况下，如果每个WebView都有不同的`UserAgent`，就会产生数据竞争的问题，大家都要修改`NSUserDefaults`中`UserAgent`的值，于是需要对资源加锁来保证每个WebView都设置预期的`UserAgent`。在Cordova中，专门有一个类`CDVUserAgentUtil`来实现这个功能。

`CDVUserAgentUtil.h`文件中定义了四个方法

```objc
// 获取UIWebView默认的UserAgent
+ (NSString*)originalUserAgent;
// 获取锁
+ (void)acquireLock:(void (^)(NSInteger lockToken))block;
// 释放锁
+ (void)releaseLock:(NSInteger*)lockToken;
// 设置UIWebView的UserAgent
+ (void)setUserAgent:(NSString*)value lockToken:(NSInteger)lockToken;
```

## 加锁

每次加锁成功会返回一个NSInteger类型的token，在释放锁的时候需要把token传入。token会不断递增，保证每次加锁返回的token都不回重复。加锁的实现代码如下：

```objc
// CDVUserAgentUtil.m
+ (void)acquireLock:(void (^)(NSInteger lockToken))block
{
    if (gCurrentLockToken == 0) {
        gCurrentLockToken = ++gNextLockToken;
        VerboseLog(@"Gave lock %d", gCurrentLockToken);
        block(gCurrentLockToken);
    } else {
        if (gPendingSetUserAgentBlocks == nil) {
            gPendingSetUserAgentBlocks = [[NSMutableArray alloc] initWithCapacity:4];
        }
        VerboseLog(@"Waiting for lock");
        [gPendingSetUserAgentBlocks addObject:block];
    }
}
```

调用`acquireLock:`，首先会判断`gCurrentLockToken`是否等于0
* 如果是0说明没有模块正在修改`UserAgent`，能够成功获取到锁，`gCurrentLockToken`递增，标致当前有模块正在修改`UserAgent`，并回调`block`，返回`gCurrentLockToken`
* 如果不为0说明当前有模块正在修改`UserAgent`，将`block`回调存在一个队列`gPendingSetUserAgentBlocks`中

## 释放锁

释放锁需要传入token，释放锁代码如下：

```objc
+ (void)releaseLock:(NSInteger*)lockToken
{
    if (*lockToken == 0) {
        return;
    }
    NSAssert(gCurrentLockToken == *lockToken, @"Got token %ld, expected %ld", (long)*lockToken, (long)gCurrentLockToken);

    VerboseLog(@"Released lock %d", *lockToken);
    if ([gPendingSetUserAgentBlocks count] > 0) {
        void (^block)() = [gPendingSetUserAgentBlocks objectAtIndex:0];
        [gPendingSetUserAgentBlocks removeObjectAtIndex:0];
        gCurrentLockToken = ++gNextLockToken;
        NSLog(@"Gave lock %ld", (long)gCurrentLockToken);
        block(gCurrentLockToken);
    } else {
        gCurrentLockToken = 0;
    }
    *lockToken = 0;
}
```

* 如果要释放的`lockToken`为0，说明还没加过锁，就调用释放了，直接返回
* 从队列`gPendingSetUserAgentBlocks`中取出最早加入的`block`，从队列中移除
* `gCurrentLockToken`递增生成新token，回调`block`
* 如果队列`gPendingSetUserAgentBlocks`释放完成，说明释放锁的调用次数>加锁的次数，不做操作，然后把`gCurrentLockToken`置为0

## 设置UserAgent

在Cordova实际运用中，操作锁的时机：
加锁时机：`CDVViewController`加载完毕，在`viewDidLoad`里调用
释放锁时机：
 * `UIWebView`的`webViewDidFinishLoad:`回调
 * `UIWebView`的`webView:didFailLoadWithError:`回调
 * `CDVViewController`的`dealloc`
 * `CDVViewController`的`viewDidUnload`

加锁代码，省略了不相关代码

```objc
// CDVViewController.m
- (void)viewDidLoad
{
    [CDVUserAgentUtil acquireLock:^(NSInteger lockToken) {
        _userAgentLockToken = lockToken;
        [CDVUserAgentUtil setUserAgent:self.userAgent lockToken:lockToken];
        NSURLRequest* appReq = [NSURLRequest requestWithURL:appURL cachePolicy:NSURLRequestUseProtocolCachePolicy timeoutInterval:20.0];
        [self.webViewEngine loadRequest:appReq];
    }];
}
```

释放锁代码，这里只看正常逻辑，在网页加载完成回调`webViewDidFinishLoad:`中释放逻辑。不考虑异常情况，省略了不相关代码。

```objc
// CDVUIWebViewNavigationDelegate.m
- (void)webViewDidFinishLoad:(UIWebView*)theWebView
{
    NSLog(@"Finished load of: %@", theWebView.request.URL);
    CDVViewController* vc = (CDVViewController*)self.enginePlugin.viewController;

    // It's safe to release the lock even if this is just a sub-frame that's finished loading.
    [CDVUserAgentUtil releaseLock:vc.userAgentLockToken];
}
```

在`webViewDidFinishLoad:`回调时，UserAgent已经设置成功，所以可以释放锁，让其它WebView操作UserDefault了


