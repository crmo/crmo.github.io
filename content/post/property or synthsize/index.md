---
title: "property or synthsize"
date: 2018-07-05T00:00:00+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2018/07/05/property or synthsize/"
tags:
  - "iOS知识小结"
draft: false
---

> 记录时间：2018.7.5

@property (nonatomic, retain) NSObject *var;

* 生成var的set、get方法的方法声明
* 生成var的set、get方法的实现（**早期版本编译器不生成**）
* 生成成员变量_var（**早期版本编译器不生成**）

@synthsize var = _var

* 生成var的set、get方法的实现
* 生成var对应的成员变量_var

> mrc年代的get、set方法的写法

```objc
- (void)setVar:(NSObject *)var {
    if (_var != var) { // 如果多次set同一个对象，如果不判断会导致对象被释放
        // 释放之前的var
        [_var release];
        _var = [var retain];
    }
}

- (NSObject *)var {
    return _var;
}
```