---
title: "URLWithString return nil"
date: 2018-07-03T00:00:00+08:00
lastmod: 2018-10-07T08:13:38.000Z
url: "/2018/07/03/URLWithString return nil/"
tags:
  - "iOS知识小结"
draft: false
---

> 记录时间：2018.7.3

## 问题描述

在使用`URLWithString`生成NSURL时，如果出现中文，会导致返回的NSURL为nil。代码如下：

```
NSURL *aUrl = [NSURL URLWithString:@"http://中文域名"];
```

[stackoverflow相关讨论](https://stackoverflow.com/questions/1981390/urlwithstring-returns-nil)

查询了[URLWithString的官方文档](https://developer.apple.com/documentation/foundation/nsurl/1572047-urlwithstring?changes=_1&language=objc)，其中有一段话解决了我的疑惑。

> This method expects URLString to contain only characters that are allowed in a properly formed URL. All other characters must be properly percent escaped. Any percent-escaped characters are interpreted using UTF-8 encoding.

意思就是该方法的输入参数`URLString`只能包含URL的合法字符，包含非法字符的URL需要进行百分号编码(percent escaped)

## 百分号编码（percent escaped）

[wiki相关词条](https://zh.wikipedia.org/wiki/百分号编码)

有两种情况必须使用百分号编码

1. 参数中出现保留字符

URL所允许的字符分作保留与未保留，保留字符是那些具有特殊含义的字符

![](15305867541997.jpg)


2. URL中出现非ASCII字符

对于非ASCII字符, 需要转换为UTF-8字节序，再进行百分号编码

## 解决方案

使用方法`stringByAddingPercentEscapesUsingEncoding`对URL字符串百分号编码。

```
NSString *encodeUrl = [url stringByAddingPercentEscapesUsingEncoding:NSUTF8StringEncoding];
    NSURL *aUrl = [NSURL URLWithString:encodeUrl];
```


