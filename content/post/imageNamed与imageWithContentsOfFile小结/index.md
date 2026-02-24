---
title: "imageNamed与imageWithContentsOfFile小结"
description: "对比 iOS 中 imageNamed 和 imageWithContentsOfFile 两种图片加载方式的缓存差异与适用场景，分析屏幕适配问题和 pathForResource 不识别 @2x 后缀的实际坑点。"
date: 2018-03-01T19:30:00+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2018/03/01/imageNamed与imageWithContentsOfFile小结/"
tags:
  - "iOS知识小结"
draft: false
---

![pexels-photo-892769](pexels-photo-892769.jpg)


> 本文主要讲imageNamed与imageWithContentsOfFile的差异，需要注意的点，与实战中遇到的坑。

好久没写过博客了，什么工作太忙，加班太晚我就不说了，都怪自己太懒😂，时间都是挤出来的。看着各位大牛写的文章，简直过瘾，希望有一天自己也能写出这么高质量、干货密集的文章，先从简单的做起吧。

## 从差异说起

从磁盘加载图片，UIImage主要提供了两种方式：

> +(UIImage *)imageNamed:(NSString *)name;
> +(UIImage *)imageWithContentsOfFile:(NSString *)path;

关于这两种方法的使用时机，苹果官方文档描述如下：

> Use the imageNamed:inBundle:compatibleWithTraitCollection: method (or the imageNamed: method) to create an image from an image asset or image file located in your app’s main bundle (or some other known bundle). Because these methods cache the image data automatically, they are especially recommended for images that you use frequently.
Use the imageWithContentsOfFile: or initWithContentsOfFile: method to create an image object where the initial data is not in a bundle. These methods load the image data from disk each time, so you should not use them to load the same image repeatedly.

也就是说，`imageNamed:`第一次加载图片时会缓存图片到内存，适合使用频繁的图片，`imageWithContentsOfFile:`不会把图片缓存到内存，每次调用都要重新从磁盘加载一次。
在实际使用中我们要根据业务来判断调用具体的方法，来最优化内存与性能。举个例子：
1. 登陆背景图，只会在用户登陆的时候使用，而且图片较大，就建议用`imageWithContentsOfFile:`加载；
2. 底导航图标，图标较小，使用频繁，就建议使用`imageNamed:`加载；

> `imageNamed:`方法还有个限制，它是在main bundle里找图片，如果图片放在`Images.xcassets`或者直接把图片方在工程里，参数直接传图片名可以找到。像我司的图片是放在单独建立的bundle里，如果要用`imageNamed:`加载的话文件名前面就要加上bundle名，像这样`a.bundle/b.png`。

## 屏幕适配问题

iOS的图片文件需要提供3种尺寸的1x、2x、3x，根据不同的屏幕尺寸我们需要加载不同的图片，关于不同屏幕的图片加载，苹果已经帮我们封装好了，我们只需要将3中尺寸的图片放到工程中，然后调用`imageNamed:`或者`imageWithContentsOfFile:`，它会自动根据屏幕尺寸来加载不同的图片。
关于`imageNamed:`，官方文档中有这么一段讨论：

> This method looks in the system caches for an image object with the specified name and returns the variant of that image that is best suited for the main screen. 

`imageWithContentsOfFile:`还没找到官方文档的说明（如果各位知道，欢迎各位大牛在评论中提出），不过我测试过是可以的。

## 使用imageWithContentsOfFile的一个坑

在使用`imageWithContentsOfFile:`加载图片的时候遇到一个坑，先上代码：

```
+ (UIImage *)imageWithName:(NSString *)name type:(NSString *)type inBundle:(NSString *)bundle {
    NSString *imageBundlePath = [[NSBundle mainBundle] pathForResource:bundle ofType:@"bundle"];
    NSBundle *imageBundle = [NSBundle bundleWithPath:imageBundlePath];
    NSString *imagePath = [imageBundle pathForResource:name ofType:type];
    UIImage *image = [UIImage imageWithContentsOfFile:imagePath];
    return image;
}
```
很简单的一个函数，就是获取bundle全路径，然后再获取到bundle里图片的全路径，然后调用`imageWithContentsOfFile:`加载图片。在使用的时候也很正常，但是有一天发现某张图加载不出来了。检查资源文件，只有2x的图（又是一个偷懒的程序员。。。很不建议这么玩，虽然只有2x的图，在所有屏幕都能显示，但是会造成图片的压缩与放大，每个细节都很重要！！！），如果加上1x的图就可以加载出来了。
经过调试发现问题就出在`pathForResource:ofType`上，这个函数是精确匹配调用者输入的文件名，不会自动识别文件名后面的`@2x`。修改后的代码：

```
+ (UIImage *)imageWithName:(NSString *)name type:(NSString *)type inBundle:(NSString *)bundle {
    NSString *imageBundlePath = [[NSBundle mainBundle] pathForResource:bundle ofType:@"bundle"];
    NSBundle *imageBundle = [NSBundle bundleWithPath:imageBundlePath];
    NSString *imageFullName = [name stringByAppendingPathExtension:type];
    NSString *imagePath = [[imageBundle resourcePath] stringByAppendingPathComponent:imageFullName];
    UIImage *image = [UIImage imageWithContentsOfFile:imagePath];
    return image;
}
```






