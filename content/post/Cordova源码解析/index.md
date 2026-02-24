---
title: "Cordova源码解析"
description: "深入解析 Cordova 4.2.1 的核心架构，包括 CDVViewController 的职责、JS 调用原生插件的完整流程（gap:// 拦截、命令队列、插件执行）、RunLoop 性能优化策略以及插件的注册与初始化机制。"
date: 2018-05-09T00:00:00+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2018/05/09/Cordova源码解析/"
tags:
  - "源码学习"
draft: false
---

本文设计到的源码是基于Cordova 4.2.1版本，[Cordova官网](https://cordova.apache.org)。

## CDVViewController

`CDVViewController`是Cordova最主要的类，它把所有模块整合在一起，直接初始化一个它的实例就可以使用。例如下面的代码：

```objc
CDVViewController *vc = [[CDVViewController alloc] init];
vc.startPage = @"www.baidu.com";
[self presentViewController:vc animated:YES completion:nil];
```

`CDVViewController`主要实现的功能：

* 注册、初始化插件
* 读取、应用配置文件
* 初始化并配置WebView，设置其代理
* 管理js与原生的方法调用
* 管理应用与网页的生命周期
。。。

 它主要的属性有：
 
* CDVWebViewEngineProtocol：webview相关的回调
* CDVCommandDelegate：js与原生插件交互方法，插件初始化
* CDVCommandQueue：命令执行队列

`CDVCommandDelegate`和`CDVCommandQueue`会在js调用原生插件与插件初始化提到，这里先不细说。
`CDVWebViewEngineProtocol`定义了`WebView`引擎的抽象类，具体实现由插件提供，例如`CDVUIWebViewEngine`实现`UIWebView`的引擎。

### CDVWebViewEngineProtocol协议定义

`CDVWebViewEngineProtocol`协议其实是对于WebView的一层封装，屏蔽了不同`WebView`接口的差异，现在iOS有`UIWebView`与`WKWebView`。

```objc
@protocol CDVWebViewEngineProtocol <NSObject>
@property (nonatomic, strong, readonly) UIView* engineWebView;

- (id)loadRequest:(NSURLRequest*)request;
- (id)loadHTMLString:(NSString*)string baseURL:(NSURL*)baseURL;
- (void)evaluateJavaScript:(NSString*)javaScriptString completionHandler:(void (^)(id, NSError*))completionHandler;
- (NSURL*)URL;
- (BOOL)canLoadRequest:(NSURLRequest*)request;
- (instancetype)initWithFrame:(CGRect)frame;
- (void)updateWithInfo:(NSDictionary*)info;
@end
```

`engineWebView`属性对外直接暴露了内部封装的`WebView`，其它方法都是对`WebView`方法的一层简单封装。

### UIWebView引擎CDVUIWebViewEngine

我们以`UIWebView`的实现`CDVUIWebViewEngine`为例说明，它是以插件的形式实现的，主要作用是初始化UIWebView的配置，对UIWebView的方法和代理进行了一层封装。它实现了协议`CDVWebViewEngineProtocol`，主要有以下几个属性。

```objc
// CDVUIWebViewEngine
// UIWebview
@property (nonatomic, strong, readwrite) UIView* engineWebView;
// UIWebView的代理
@property (nonatomic, strong, readwrite) id <UIWebViewDelegate> uiWebViewDelegate;
@property (nonatomic, strong, readwrite) CDVUIWebViewNavigationDelegate* navWebViewDelegate;
```

初始化从`initWithFrame:`方法开始，它创建了一个`UIWebView`，并赋值给了`engineWebView`，然后在插件初始化方法`pluginInitialize`中初始化`UIWebView`的代理和配置。

```objc
- (void)pluginInitialize
{
    UIWebView* uiWebView = (UIWebView*)_engineWebView;

    // 判断当前controller是否实现了UIWebViewDelegate
    // 如果实现了就把当前controller设置为CDVUIWebViewDelegate的代理实现
    if ([self.viewController conformsToProtocol:@protocol(UIWebViewDelegate)]) {
        self.uiWebViewDelegate = [[CDVUIWebViewDelegate alloc] initWithDelegate:(id <UIWebViewDelegate>)self.viewController];
        uiWebView.delegate = self.uiWebViewDelegate;
    } 
    // 如果没有实现，创建一个CDVUIWebViewNavigationDelegate，作为CDVUIWebViewDelegate的代理实现
    else {
        self.navWebViewDelegate = [[CDVUIWebViewNavigationDelegate alloc] initWithEnginePlugin:self];
        self.uiWebViewDelegate = [[CDVUIWebViewDelegate alloc] initWithDelegate:self.navWebViewDelegate];
        uiWebView.delegate = self.uiWebViewDelegate;
    }

    // 初始化配置信息
    // self.commandDelegate.settings是CDVViewController的配置信息，定义在config.xml
    [self updateSettings:self.commandDelegate.settings];
}
```

## js调用原生插件解析

插件调用流程：

1. js发起请求`gap://`
2. 实现`WebView`的代理`webView:shouldStartLoadWithRequest:navigationType:`，拦截`scheme`为`gap`的请求
3. 执行js方法`cordova.require('cordova/exec').nativeFetchMessages()`获取需要执行的原生插件的信息（插件名，插件方法，回调ID，参数）
4. 将需要执行的原生插件信息放入命令队列等待执行
5. 执行原生插件，并把结果回调给js

插件调用堆栈如图所示：

![](15256629038423.jpg)

### js请求拦截

`CDVUIWebViewDelegate`实现了UIWebView的`webView:shouldStartLoadWithRequest:navigationType:`代理，在页面加载前做一些处理。

```objc
- (BOOL)webView:(UIWebView*)webView shouldStartLoadWithRequest:(NSURLRequest*)request navigationType:(UIWebViewNavigationType)navigationType
{
    BOOL shouldLoad = YES;

    // 1. 判断如果有代理，先调用代理方法
    // 这里的_delegate是CDVUIWebViewNavigationDelegate
    if ([_delegate respondsToSelector:@selector(webView:shouldStartLoadWithRequest:navigationType:)]) {
        shouldLoad = [_delegate webView:webView shouldStartLoadWithRequest:request navigationType:navigationType];
    }

    if (shouldLoad) {
        // 是否是调试工具refresh
        BOOL isDevToolsRefresh = (request == webView.request);
        // 是否是顶层页面
        BOOL isTopLevelNavigation = isDevToolsRefresh || [request.URL isEqual:[request mainDocumentURL]];
        
        if (isTopLevelNavigation) {
            if ([self request:request isEqualToRequestAfterStrippingFragments:webView.request]) {
                NSString* prevURL = [self evalForCurrentURL:webView];
                if ([prevURL isEqualToString:[request.URL absoluteString]]) {
                    VerboseLog(@"Page reload detected.");
                } else {
                    VerboseLog(@"Detected hash change shouldLoad");
                    return shouldLoad;
                }
            }

            switch (_state) {
                case STATE_WAITING_FOR_LOAD_FINISH:
                    // 重定向情况，判断loadCount是否是1
                    if (_loadCount != 1) {
                        NSLog(@"CDVWebViewDelegate: Detected redirect when loadCount=%ld", (long)_loadCount);
                    }
                    break;

                case STATE_IDLE:
                case STATE_IOS5_POLLING_FOR_LOAD_START:
                case STATE_CANCELLED:
                    // 页面导航开始
                    _loadCount = 0;
                    _state = STATE_WAITING_FOR_LOAD_START;
                    break;

                default:
                    {
                        // 其它情况，回调webView:didFailLoadWithError:
                        NSString* description = [NSString stringWithFormat:@"CDVWebViewDelegate: Navigation started when state=%ld", (long)_state];
                        NSLog(@"%@", description);
                        _loadCount = 0;
                        _state = STATE_WAITING_FOR_LOAD_START;
                        if ([_delegate respondsToSelector:@selector(webView:didFailLoadWithError:)]) {
                            NSDictionary* errorDictionary = @{NSLocalizedDescriptionKey : description};
                            NSError* error = [[NSError alloc] initWithDomain:@"CDVUIWebViewDelegate" code:1 userInfo:errorDictionary];
                            [_delegate webView:webView didFailLoadWithError:error];
                        }
                    }
            }
        } else {
            // 屏蔽一些无效网站的访问
            shouldLoad = shouldLoad && [self shouldLoadRequest:request];
        }
    }
    return shouldLoad;
}
```

拦截js调用原生插件请求的关键代码在`CDVUIWebViewNavigationDelegate`，它实现了`CDVUIWebViewDelegate`的代理，在`CDVUIWebViewDelegate`会把请求转发给它。

```objc
- (BOOL)webView:(UIWebView*)theWebView shouldStartLoadWithRequest:(NSURLRequest*)request navigationType:(UIWebViewNavigationType)navigationType
{
    NSURL* url = [request URL];
    CDVViewController* vc = (CDVViewController*)self.enginePlugin.viewController;
    
    // H5调用原生插件，后面分析
    if ([[url scheme] isEqualToString:@"gap"]) {
        [vc.commandQueue fetchCommandsFromJs];
        [vc.commandQueue executePending];
        return NO;
    }

    // 给插件预留了一个处理URL的方法，调用插件的方法`shouldOverrideLoadWithRequest:navigationType:`，获取返回值
    // 应用：系统默认插件CDVIntentAndNavigationFilter中，实现了Intent与Navigation的白名单机制。
    BOOL anyPluginsResponded = NO;
    BOOL shouldAllowRequest = NO;
    
    for (NSString* pluginName in vc.pluginObjects) {
        CDVPlugin* plugin = [vc.pluginObjects objectForKey:pluginName];
        SEL selector = NSSelectorFromString(@"shouldOverrideLoadWithRequest:navigationType:");
        if ([plugin respondsToSelector:selector]) {
            anyPluginsResponded = YES;
            shouldAllowRequest = (((BOOL (*)(id, SEL, id, int))objc_msgSend)(plugin, selector, request, navigationType));
            if (!shouldAllowRequest) {
                break;
            }
        }
    }
    
    if (anyPluginsResponded) {
        return shouldAllowRequest;
    }

     // 处理其它类型的url,file:类型直接返回YES
    BOOL shouldAllowNavigation = [self defaultResourcePolicyForURL:url];
    if (shouldAllowNavigation) {
        return YES;
    } else {
        [[NSNotificationCenter defaultCenter] postNotification:[NSNotification notificationWithName:CDVPluginHandleOpenURLNotification object:url]];
    }
    
    return NO;
}
```

### H5调用原生插件

Cordova调用原生插件的方式是通过拦截`gap://`的URL，然后执行js代码`cordova.require('cordova/exec').nativeFetchMessages()`获取参数，来实现调用。

我们来看关键代码：

```objc
// CDVUIWebViewNavigationDelegate.m
- (BOOL)webView:(UIWebView*)theWebView shouldStartLoadWithRequest:(NSURLRequest*)request navigationType:(UIWebViewNavigationType)navigationType
{
    CDVViewController* vc = (CDVViewController*)self.enginePlugin.viewController;
    
    if ([[url scheme] isEqualToString:@"gap"]) {
        [vc.commandQueue fetchCommandsFromJs];
        [vc.commandQueue executePending];
        return NO;
    }
}
```

```objc
- (void)fetchCommandsFromJs
{
    __weak CDVCommandQueue* weakSelf = self;
    NSString* js = @"cordova.require('cordova/exec').nativeFetchMessages()";

    [_viewController.webViewEngine evaluateJavaScript:js
                                    completionHandler:^(id obj, NSError* error) {
        if ((error == nil) && [obj isKindOfClass:[NSString class]]) {
            NSString* queuedCommandsJSON = (NSString*)obj;
            // 调用的插件信息加入到queue中
            [weakSelf enqueueCommandBatch:queuedCommandsJSON];
            // 调用执行方法
            [self executePending];
        }
    }];
}
```

调用js方法`cordova.require('cordova/exec').nativeFetchMessages()`，获取调用的插件信息。

```json
// 插件信息示例
[["DevicePlugin1678563772","DevicePlugin","getDeviceInfo",[]]]
```

### 命令队列CDVCommandQueue

js的每次调用信息会封装被封装为一个命令`CDVInvokedUrlCommand`，`CDVInvokedUrlCommand`继承自`NSObject`，主要存储了下面的信息：

```objc
// CDVInvokedUrlCommand
// 参数
@property (nonatomic, readonly) NSArray* arguments;
// 回调ID
@property (nonatomic, readonly) NSString* callbackId;
// 类名
@property (nonatomic, readonly) NSString* className;
// 方法名
@property (nonatomic, readonly) NSString* methodName;
```

`CDVCommandQueue`管理着所有的命令，实现了一个命令的队列。在js调用原生插件时，会调用`CDVCommandQueue`的`enqueueCommandBatch:`方法，将插件调用信息加到`commandBatchHolder`数组中，最后`commandBatchHolder`数组添加到`CDVCommandQueue`的`queue`。

```objc
- (void)enqueueCommandBatch:(NSString*)batchJSON
{
    if ([batchJSON length] > 0) {
        NSMutableArray* commandBatchHolder = [[NSMutableArray alloc] init];
        [_queue addObject:commandBatchHolder];
        if ([batchJSON length] < JSON_SIZE_FOR_MAIN_THREAD) {
            [commandBatchHolder addObject:[batchJSON cdv_JSONObject]];
        } else {
            dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^() {
                NSMutableArray* result = [batchJSON cdv_JSONObject];
                @synchronized(commandBatchHolder) {
                    [commandBatchHolder addObject:result];
                }
                [self performSelectorOnMainThread:@selector(executePending) withObject:nil waitUntilDone:NO];
            });
        }
    }
}
```

插件的执行由`CDVCommandQueue`管理，每个`CDVViewController`有自己的队列，有两个重要的成员变量。

```objc
    /* 二维数组，存储着所有插件调用的json */
    NSMutableArray* _queue;
    /* 记录开始调用的时间 */
    NSTimeInterval _startExecutionTime;
```

`executePending`负责执行命令队列中待执行的插件，具体实现就是遍历执行二维数组`queue`。

```objc
- (void)executePending
{
    // 如果已经开始执行了，返回
    if (_startExecutionTime > 0) {
        return;
    }
    @try {
        // 记录开始执行的时间
        _startExecutionTime = [NSDate timeIntervalSinceReferenceDate];

        // 遍历_queue
        while ([_queue count] > 0) {
            NSMutableArray* commandBatchHolder = _queue[0];
            NSMutableArray* commandBatch = nil;
            @synchronized(commandBatchHolder) {
                if ([commandBatchHolder count] == 0) {
                    break;
                }
                commandBatch = commandBatchHolder[0];
            }
            
            // 遍历commandBatch
            while ([commandBatch count] > 0) {
                @autoreleasepool {
                    // 取出commandBatch的第一条数据，并移除
                    NSArray* jsonEntry = [commandBatch cdv_dequeue];
                    if ([commandBatch count] == 0) {
                        [_queue removeObjectAtIndex:0];
                    }
                    
                    // 用插件调用json信息，创建CDVInvokedUrlCommand
                    CDVInvokedUrlCommand* command = [CDVInvokedUrlCommand commandFromJson:jsonEntry];

                    // 调用插件
                    [self execute:command]);
                }

                // 对于性能的一个优化，后面会详细说
                if (([_queue count] > 0) && ([NSDate timeIntervalSinceReferenceDate] - _startExecutionTime > MAX_EXECUTION_TIME)) {
                    [self performSelector:@selector(executePending) withObject:nil afterDelay:0];
                    return;
                }
            }
        }
    } @finally
    {
        _startExecutionTime = 0;
    }
}
```

### 用Runloop优化性能

Cordova对于插件的执行进行了优化，保证页面的流程度，运用了RunLoop，巧妙的将代码分割为多块分次执行，避免由于插件执行导致主线程阻塞，影响页面绘制，导致掉帧。具体代码如下：

```objc
// CDVCommandQueue.m

// MAX_EXECUTION_TIME ≈ 1s / 60 / 2
// 计算出绘制一帧时间的一半
static const double MAX_EXECUTION_TIME = .008;

// 判断本次执行时间，如果大于MAX_EXECUTION_TIME，调用performSelector:withObject:afterDelay，结束本次调用
if (([_queue count] > 0) && ([NSDate timeIntervalSinceReferenceDate] - _startExecutionTime > MAX_EXECUTION_TIME)) {
    [self performSelector:@selector(executePending) withObject:nil afterDelay:0];
    return;
}
```

优化策略分析：

* 将队列中的插件分割为很多小块来执行
* 开始执行`executePending`方法时，记录开始时间，每次执行完一个插件方法后，判断本次执行时间是否超过`MAX_EXECUTION_TIME`，如果没有超过，继续执行，如果超过了`MAX_EXECUTION_TIME`，调用`performSelector:withObject:afterDelay`，结束本次调用
* 如果要保证UI流畅，需要满足条件`CPU时间 + GPU时间 <= 1s/60`， 为了给GPU留下足够的时间渲染，要尽量让CPU占用时间小于`1s/60/2`
* Runloop执行的流程如下图所示，系统在收到`kCFRunLoopBeforeWaiting`（线程即将休眠）通知时，会触发一次界面的渲染，也就是在完成`source0`的处理后
* `source0`在这里就是插件的执行代码，在`kCFRunLoopBeforeWaiting`通知之前，如果`source0`执行时间过长就会导致界面没有得到及时的刷新。
* 函数`performSelector:withObject:afterDelay`，会将方法注册到`Timer`，结束`source0`调用，开始渲染界面。界面渲染完成后，`Runloop`开始`sleep`，然后被`timer`唤醒又开始继续处理`source0`。

![](15256833278020.png)

### 插件方法执行

方法最终的执行在方法`execute:`中，从command中取出要执行的插件类、方法、参数，然后执行方法。

```objc
- (BOOL)execute:(CDVInvokedUrlCommand*)command
{
    // 获取插件实例
    CDVPlugin* obj = [_viewController.commandDelegate getCommandInstance:command.className];

    BOOL retVal = YES;
    double started = [[NSDate date] timeIntervalSince1970] * 1000.0;
    
    NSString* methodName = [NSString stringWithFormat:@"%@:", command.methodName];
    SEL normalSelector = NSSelectorFromString(methodName);
    if ([obj respondsToSelector:normalSelector]) {
        ((void (*)(id, SEL, id))objc_msgSend)(obj, normalSelector, command);
    } else {
        // There's no method to call, so throw an error.
        NSLog(@"ERROR: Method '%@' not defined in Plugin '%@'", methodName, command.className);
        retVal = NO;
    }
    double elapsed = [[NSDate date] timeIntervalSince1970] * 1000.0 - started;
    // 监控插件方法执行时间，打印出大于10ms的方法
    if (elapsed > 10) {
        NSLog(@"THREAD WARNING: ['%@'] took '%f' ms. Plugin should use a background thread.", command.className, elapsed);
    }
    return retVal;
}
```

### 原生回调js

原生方法执行完成后，会把结果返回给js，调用方法`sendPluginResult:callbackId:`，用`CDVPluginResult`来传递回调参数，用`callbackId`来区分是哪次调用（callbackId由js产生）。

```objc
// CDVCommandDelegateImpl.m
- (void)sendPluginResult:(CDVPluginResult*)result callbackId:(NSString*)callbackId
{
    // 判断callbackId长度是否小于100
    // 用正则表达式"[^A-Za-z0-9._-]"来验证callbackId
    if (![self isValidCallbackId:callbackId]) {
        return;
    }
    // 状态码
    int status = [result.status intValue];
    // 是否持续回调
    BOOL keepCallback = [result.keepCallback boolValue];
    // 会带哦参数
    NSString* argumentsAsJSON = [result argumentsAsJSON];
    
    // 执行js方法，回调
    NSString* js = [NSString stringWithFormat:@"cordova.require('cordova/exec').nativeCallback('%@',%d,%@,%d, %d)", callbackId, status, argumentsAsJSON, keepCallback, debug];
    [self evalJsHelper:js];
}
```


## CDVPlugin注册与初始化

我们先看看配置文件中插件的定义：

```xml
<!-- 定义插件名为HandleOpenUrl的插件 -->
<feature name="HandleOpenUrl">
    <!-- 对应的iOS类名是CDVHandleOpenURL -->
    <param name="ios-package" value="CDVHandleOpenURL" />
    <!-- 需要默认加载的插件 -->
    <param name="onload" value="true" />
</feature>
```

### 加载默认插件

在`CDVViewController`的`viewDidLoad`时，从Cordova的配置文件`config.xml`中，读取出需要默认加载的插件，遍历初始化。

`CDVViewController`中初始化默认插件代码。

```objc
- (void)viewDidLoad {
    // Load settings
    [self loadSettings];
    
    if ([self.startupPluginNames count] > 0) {
        [CDVTimer start:@"TotalPluginStartup"];
        
        for (NSString* pluginName in self.startupPluginNames) {
            [CDVTimer start:pluginName];
            // 初始化插件
            [self getCommandInstance:pluginName];
            [CDVTimer stop:pluginName];
        }
        
        [CDVTimer stop:@"TotalPluginStartup"];
    }
}
```

### 插件初始化

插件初始化的过程：
1. 加载配置文件`config.xml`
2. 根据插件名获取对应类名
3. 根据类名从缓存中查找，如果命中直接返回
4. 没有缓存重新创建一个实例，并写入缓存

插件初始化的入口是`getCommandInstance`，传入参数是插件名称，返回一个插件的实例对象。

```objc
- (id)getCommandInstance:(NSString*)pluginName
{
    // 在pluginsMap中用插件名称获取类名（插件名不区分大小写）
    NSString* className = [self.pluginsMap objectForKey:[pluginName lowercaseString]];
    
    // 没有配置插件，初始化失败
    if (className == nil) {
        return nil;
    }
    
    // 从缓存中获取，如果命中直接返回缓存
    id obj = [self.pluginObjects objectForKey:className];
    if (!obj) {
        // 没有缓存，创建一个新的实例
        obj = [[NSClassFromString(className)alloc] initWithWebViewEngine:_webViewEngine];
        
        if (obj != nil) {
            // 实例创建成功，注册插件
            [self registerPlugin:obj withClassName:className];
        } else {
            NSLog(@"CDVPlugin class %@ (pluginName: %@) does not exist.", className, pluginName);
        }
    }
    return obj;
}
```

注册插件的关键方法`registerPlugin:withClassName:`

```objc
- (void)registerPlugin:(CDVPlugin*)plugin withClassName:(NSString*)className
{
    if ([plugin respondsToSelector:@selector(setViewController:)]) {
        [plugin setViewController:self];
    }
    
    if ([plugin respondsToSelector:@selector(setCommandDelegate:)]) {
        [plugin setCommandDelegate:_commandDelegate];
    }
    
    // 写入缓存
    [self.pluginObjects setObject:plugin forKey:className];
    [plugin pluginInitialize];
}
```

Cordova还提供了插件名注册插件的方式，使用函数`registerPlugin:withPluginName:`，实现方式差不多，就不赘述了。

注册插件步骤
1. 设置插件的`viewController`和`delegate`
2. 将插件以`className`为key放入`pluginObjects`中，`pluginObjects`是一个插件的缓存
3. 调用插件的`pluginInitialize`

### 插件销毁

插件销毁的时机是创建插件的`CDVViewController`释放的时候，因为插件实例被创建后被缓存map引用，对应的销毁代码。

```objc
// CDVViewController.m
- (void)dealloc
{
    [[NSNotificationCenter defaultCenter] removeObserver:self];
    
    [CDVUserAgentUtil releaseLock:&_userAgentLockToken];
    [_commandQueue dispose];
    [[self.pluginObjects allValues] makeObjectsPerformSelector:@selector(dispose)];
}

// CDVPlugin.m
- (void)dispose
{
    viewController = nil;
    commandDelegate = nil;
}
```
### 小结

1. 在`config.xml`文件中配置插件，声明插件与类的映射关系，以及加载策略
2. 插件的初始化时懒加载，除了`onload`配置为`YES`的插件会默认加载，其它插件都是使用时加载
3. 插件使用了两个Map来缓存，`pluginObjects`建立了类名与插件实例对象的映射，`pluginsMap`建立了插件名与类名的映射。
4. 在一个`CDVViewController`中，同一个插件同时只会存在一个实例



