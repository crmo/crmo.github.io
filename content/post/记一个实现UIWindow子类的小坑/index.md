---
title: "记一个实现UIWindow子类的小坑"
date: 2018-07-19T00:00:00+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2018/07/19/记一个实现UIWindow子类的小坑/"
tags:
  - "iOS知识小结"
draft: false
---

> 2018.7.19

## 问题描述

项目中为了实现一个全局遮罩界面，使用了一个UIWindow的子类`MyWindow`，`MyWindow`为了实现回调定义了代理`MyWindowDelegate`。代码大致如下：

```objectivec
@protocol MyWindowDelegate <NSObject>
@end

@interface MyWindow : UIWindow
@property (nonatomic, assign)id<MyWindowDelegate> delegate;
@end

@implementation MyWindow
- (instancetype)init
{
    self = [super init];
    if (self) {
        self.windowLevel = UIWindowLevelNormal;
        self.backgroundColor = [UIColor whiteColor];
        UIViewController *vc = [[ViewController2 alloc] init];
        self.rootViewController = vc;
        self.hidden = NO;
    }
    return self;
}
@end
```

然后在实现界面横屏时，发现整个UIWindow不响应横竖屏事件。刚开始以为横竖屏设置被关闭了，查了各种资料，发现这种写法是没有问题的。设置UIWindow的rootViewController，然后把所有子view都加到rootViewController，系统会处理横竖屏问题。


## 问题分析

用Runtime把UIWindow的私有变量打出来，就发现问题了。

```objectivec
#import <objc/runtime.h>

- (void)printUIWindowIvars {
    Ivar *ivars = class_copyIvarList([UIWindow class], &count);
    for (int i = 0; i < count; i++) {
        Ivar ivar = ivars[i];
        NSLog(@"%s", ivar_getName(ivar));
    }
}
```

我们看看输出，发现有个私有变量`_delegate`。

![](15319834677166.jpg)

`MyWindow`的属性`delegate`覆盖了父类`UIWindow`的变量，导致横竖屏切换事件失效。在代理命名的时候一定要注意啊，`delegate`看来不是一个好的实践，应该加前缀区分避免覆盖父类的实现，特别是这种私有的变量。