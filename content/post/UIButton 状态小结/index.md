---
title: "UIButton 状态小结"
date: 2019-10-07T00:00:00+08:00
lastmod: 2019-10-07T07:57:56.000Z
url: "/2019/10/07/UIButton 状态小结/"
tags:
  - "iOS知识小结"
draft: false
---

## 案例

我们先从一个问题说起，小明同学接到产品的一个新需求：实现一个 `UIButton`，要求在 normal、selected、highlighted 三种状态下展示不同文案。这简直太简单了，小明同学1分钟不到就实现了，关键代码如下：

```objc
[button setTitle:@"normal" forState:UIControlStateNormal];
[button setTitle:@"highlighted" forState:UIControlStateHighlighted];
[button setTitle:@"selected" forState:UIControlStateSelected];
```

这段代码有什么问题吗？

的确有问题！当 `button` 状态为 `selected` 时，点击按钮，文案展示 `normal`，当前状态应该是 `UIControlStateHighlighted`，怎么展示了 `UIControlStateNormal` 的文案？

## 问题分析

`UIButton` 有5种状态，分别是：default(normal), highlighted, focused, selected, disabled，通过属性 `state` 可以拿到当前状态值 `UIControlState`，定义如下：

```objc
@property(nonatomic,readonly) UIControlState state;                  // could be more than one state (e.g. disabled|selected). synthesized from other flags.

typedef NS_OPTIONS(NSUInteger, UIControlState) {
    UIControlStateNormal       = 0,
    UIControlStateHighlighted  = 1 << 0,                  // used when UIControl isHighlighted is set
    UIControlStateDisabled     = 1 << 1,
    UIControlStateSelected     = 1 << 2,                  // flag usable by app (see below)
    UIControlStateFocused NS_ENUM_AVAILABLE_IOS(9_0) = 1 << 3, // Applicable only when the screen supports focus
};
```

看到位运算我们就可以猜到这个状态可以组合，而且有句很关键的注释：

> could be more than one state (e.g. disabled|selected). synthesized from other flags.
state 不是单独的状态，可以是多种状态的混合。

我们在回到上面的小明同学遇到的问题，当 `button` 状态为 `selected` 时，点击按钮，按钮此时的状态其实是 `UIControlStateHighlighted | UIControlStateSelected`。在[官方文档](https://developer.apple.com/documentation/uikit/uibutton/1624018-settitle?language=objc)中，我们可以看到这么一句话：

> If a title is not specified for a state, the default behavior is to use the title associated with the UIControlStateNormal state

也就是说小明同学其实漏设置了一种状态，然后系统展示了按钮的默认状态 `UIControlStateNormal`，按钮状态并不是是 `UIControlStateNormal`。

## 小结

1、`UIControlState` 是个组合状态，在 `setTitle:forState:`、`setImage:forState:` 时，如果需要自定义 `UIControlStateSelected` 状态，一定要注意自定义 `UIControlStateHighlighted | UIControlStateSelected`。
2、如果按钮的当前状态没有自定义，使用 `UIControlStateNormal` 定义的值。