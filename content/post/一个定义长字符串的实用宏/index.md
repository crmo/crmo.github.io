---
title: "一个定义长字符串的实用宏"
description: "介绍从 WebViewJavascriptBridge 源码中发现的字符串化宏技巧，用 #x 预处理运算符优雅地在 Objective-C 中定义多行长字符串，并演示如何用 Xcode 查看宏展开结果。"
date: 2018-10-16T00:00:00+08:00
lastmod: 2018-10-17T00:53:35.361Z
url: "/2018/10/16/一个定义长字符串的实用宏/"
tags:
  - "iOS知识小结"
draft: false
---

> 2018.10.16

今天在看`WebViewJavascriptBridge`源码的时候发现一个神奇的宏，在定义较长字符串时很实用。
举个例子，将一段js代码存到一个变量，为了便于阅读需要加入换行，需要在每行结束加上`\`。

```objectivec
NSString *str = @"function() { \
	if (window.WebViewJavascriptBridge) { \
		return; \
	} \
})(); \
	";
```

这时，可以用宏来优化。

```objectivec
#define LONG_STRING_DEFINE(x) #x
NSString *str = @LONG_STRING_DEFINE(function() {
	if (window.WebViewJavascriptBridge) {
		return;
	}
})();
	);
```

宏展开后代码如下

```objectivec
NSString *str = @";(function() { if (window.WebViewJavascriptBridge) { return; })();";
```

## 用Xcode看宏展开

打开`Assistant Editor`，选择`Preproces`，就可以看到展开的宏。

![](15396963641371.jpg)

