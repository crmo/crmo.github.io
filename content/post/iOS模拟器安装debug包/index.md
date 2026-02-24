---
title: "iOS模拟器安装debug包"
description: "介绍如何将 Xcode 编译的 debug 包拷贝到其他机器的 iOS 模拟器上运行，使用 ios-sim 工具完成安装和启动，解决无源码调试 Hybrid H5 的需求。"
date: 2018-08-21T00:00:00+08:00
lastmod: 2019-03-07T01:03:01.000Z
url: "/2018/08/21/iOS模拟器安装debug包/"
tags:
  - "iOS知识小结"
draft: false
---

> 2018.8.21

由于项目是Hybrid的平台，有第三方人员需要在上面开发H5应用，但是release包不能调试H5，只有debug报可以调试，但是项目源码不能交给第三方，在google搜索了下，发现一篇霜神的[文章](https://juejin.im/post/57b01f298ac247005f0acb0a)，讲的是debug包可以拷贝到其它机器运行，于是实践了一波。

## 环境准备

* Xcode
* Command Line Tools
* ios-sim

> ios-sim安装命令：npm install ios-sim -g

## 拷贝本地的debug包

 1. run一次需要拷贝的项目，安装到模拟器上


 2. 执行下面命令行，需要注意的是`目标路径/xxx.zip`就是拷贝出来的debug应用包，需要替换为自己的路径，例如`/Users/crmo/Desktop/debug/debug.zip`

```
ditto -ck --sequesterRsrc --keepParent `ls -1 -d -t ~/Library/Developer/Xcode/DerivedData/*/Build/Products/*-iphonesimulator/*.app | head -n 1` 目标路径/xxx.zip
```

## 拷贝debug包到其它模拟器

### 1. 获取模拟器列表

> ios-sim showdevicetypes

可以看到类似于下面的输出，就是本机可用的模拟器，选择一个需要运行的模拟器。

```
~ ios-sim showdevicetypes
Apple-Watch-38mm, watchOS 4.3
Apple-Watch-42mm, watchOS 4.3
Apple-Watch-Series-2-38mm, watchOS 4.3
Apple-Watch-Series-2-42mm, watchOS 4.3
iPhone-7-Plus, 10.3
iPhone-7-Plus, 11.4
Apple-Watch-Series-3-38mm, watchOS 4.3
Apple-Watch-Series-3-42mm, watchOS 4.3
iPhone-5s, 11.4
iPhone-6, 11.4
iPhone-6-Plus, 11.4
iPhone-6s, 11.4
iPhone-6s-Plus, 11.4
iPhone-7, 11.4
iPhone-SE, 11.4
iPad-Air, 11.4
iPad-Air-2, 11.4
iPhone-8, 11.4
iPhone-8-Plus, 11.4
iPhone-X, 11.4
```

### 2. 在模拟器上启动debug包

> ios-sim launch 应用包路径/xxx.app --devicetypeid 模拟器

需要说明的是，debug.zip解压后就可以得到对应应用的.app文件，例如我的debug包放在`/Users/crmo/Desktop/debug/debug.app`，模拟器选择iPhone-8，最终的命令是

> ios-sim launch /Users/crmo/Desktop/debug/debug.app --devicetypeid iPhone-8

或者将应用直接安装到模拟器上

> ios-sim install /Users/crmo/Desktop/debug/debug.app --devicetypeid iPhone-8

## simctl was not found错误解决

在实践时测试机的`Command Line Tools`没有配置好，出现报错：

```
simctl was not found.
Check that you have Xcode 8.x installed:
	xcodebuild --versionCheck that you have Xcode 8.x selected:
	xcode-select --print-path
```

**解决办法：**

1.首先确保正确安装了Command Line Tools，

> 卸载Command Line Tools:rm -rf /Library/Developer/CommandLineTools
> 安装Command Line Tools:xcode-select --install
    
2.在xcode配置一下Command Line Tools，如下图所示

![](15348328228775.jpg)

---

参考博客：
* [unable to find utility "simctl"的解决方案](http://www.hudongdong.com/bug/772.html)
* [给 iOS 模拟器 “安装”app 文件](https://juejin.im/post/57b01f298ac247005f0acb0a)