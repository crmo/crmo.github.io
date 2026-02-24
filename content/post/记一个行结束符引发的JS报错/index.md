---
title: "记一个行结束符引发的JS报错"
description: "记录 UIWebView 执行 JavaScript 时因 U+2028/U+2029 行分隔符导致 SyntaxError 的问题，分析原因并给出过滤这两个特殊字符的解决方案。"
date: 2018-09-05T00:00:00+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2018/09/05/记一个行结束符引发的JS报错/"
tags:
  - "iOS知识小结"
draft: false
---

> 2018.9.5

## 问题描述

最近遇到一个神奇的Bug，通过`UIWebView`的`stringByEvaluatingJavaScriptFromString:`方法执行一段`JavaScript`代码时，`JavaScript`报错:

> SyntaxError: Unexpected EOF

经过仔细的排查，发现待执行的`JavaScript`代码里面包含`U+2028`字符。还找到了[Stack Overflow相关讨论](https://stackoverflow.com/questions/2965293/javascript-parse-error-on-u2028-unicode-character)。
`JavaScript`解析器会把行分隔符`U+2028`和段落分隔符`U+2029`解析成一行的结束，代码里要是包含这两个字符相当于换行，例如：

> alert("\u2028")

就会被解析为

> alert("
> ")

于是就产生了语法错误。

## 解决方案

我用的方法比较简单、粗暴，在执行`JavaScript`代码前，直接过滤掉这两个字符。代码如下：

```objc
// 
    javaScriptString = [javaScriptString stringByReplacingOccurrencesOfString:@"\u2028" withString:@""];
    javaScriptString = [javaScriptString stringByReplacingOccurrencesOfString:@"\u2029" withString:@""];
    NSString* ret = [(UIWebView*)_engineWebView stringByEvaluatingJavaScriptFromString:javaScriptString];
```

