---
title: "iOS消息转发小记"
date: 2018-05-31T00:00:00+08:00
lastmod: 2018-10-07T08:13:38.000Z
url: "/2018/05/31/iOS消息转发小记/"
tags:
  - "iOS知识小结"
draft: false
---

消息转发流程图

![](15277558865032.jpg)

如果类接收到无法处理的消息，会触发消息转发机制，一共有三个步骤，接受者在每一步中均有机会处理消息。步骤越往后，处理消息的代价就越大，所以最好再第一步就处理完。

## 第一道防线

在类里面实现两个方法来处理未知消息。执行动态方法解析之前，先会判断是否曾经有动态解析。

* `resolveInstanceMethod`：处理实例方法
* `resolveClassMethod`：处理类方法

我们来看个Demo，先看调用方代码

```objc
    TestA *testA = [[TestA alloc] init];
    [testA instanceMethod];
    [TestA classMethod];
```

再来看看TestA的定义。

```objc
// TestA.h
@interface TestA : NSObject

- (void)instanceMethod;
+ (void)classMethod;

@end

// TestA.m
@implementation TestA

- (void)newInstanceMethod {
    NSLog(@"newInstanceMethod");
}

+ (void)newClassMethod {
    NSLog(@"newClassMethod");
}

+ (BOOL)resolveInstanceMethod:(SEL)sel {
    if (sel == @selector(instanceMethod)) {
        // 动态添加方法newInstanceMethod
        Method method = class_getInstanceMethod([self class], @selector(newInstanceMethod));
        IMP imp = method_getImplementation(method);
        class_addMethod([self class], sel, imp, method_getTypeEncoding(method));
        // 成功处理，消息转发机制结束，调用newInstanceMethod
        return YES;
    }
    // 不能处理，进入第二步
    return [super resolveInstanceMethod:sel];
}

+ (BOOL)resolveClassMethod:(SEL)sel {
    if (sel == @selector(classMethod)) {
        // 动态添加方法newClassMethod
        Method method = class_getInstanceMethod(object_getClass(self), @selector(newClassMethod));
        IMP imp = method_getImplementation(method);
        class_addMethod(object_getClass(self), sel, imp, method_getTypeEncoding(method));
        // 成功处理，消息转发机制结束，调用newClassMethod
        return YES;
    }
    // 不能处理，进入第二步
    return [super resolveClassMethod:sel];
}

@end
```

TestA中头文件定义了两个方法，但是没有实现，如果不用消息转发机制处理异常，会导致crash，log想必大家应该很熟悉

> *** Terminating app due to uncaught exception 'NSInvalidArgumentException', reason: '-[TestA funcA]: unrecognized selector sent to instance 0x6040000125c0'

实例方法存储在类对象，类方法存储在元类对象，在调用`class_addMethod`时，第一个参数需要注意。

## 第二道防线

第二道防线依赖一个函数`forwardingTargetForSelector`。

```objc
// 类方法
//+ (id)forwardingTargetForSelector:(SEL)aSelector {
//    
//}
- (id)forwardingTargetForSelector:(SEL)aSelector {
    if (aSelector == @selector(instanceMethod)) {
        // 消息转发给TestB实例
        return [TestB new];
    }
    // 消息转发失败，进入下一步
    return nil;
}

// TestB.m
- (void)instanceMethod {
    NSLog(@"instanceMethod");
}
```

## 第三道防线

第三道防线有两步

1. 调用`methodSignatureForSelector`，获取新的方法签名（返回值类型，参数类型）
2. 调用`forwardInvocation`，转发消息，


```objc
// 方法签名（返回值类型，参数类型）
// 类方法减号改为加号
- (NSMethodSignature *)methodSignatureForSelector:(SEL)aSelector {
    NSMethodSignature *signature = [TestB instanceMethodSignatureForSelector:aSelector];
    return signature;
}

// NSInvocation封装了方法调用，包括：方法调用者、方法名、方法参数
// anInvocation.target 消息接受者
// anInvocation.selector 函数名
// [anInvocation getArgument:NULL atIndex:0]; 获取参数
// 类方法减号改为加号
- (void)forwardInvocation:(NSInvocation *)anInvocation {
    [anInvocation invokeWithTarget:[TestB new]];
}
```

