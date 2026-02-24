---
title: "App Store上架漫谈"
description: "分享独立 APP「识之」的 App Store 上架审核经验，包括如何阅读理解苹果审核拒信、录制演示视频辅助审核、以及应对 Guideline 3.1.4 和 4.2 条款被拒的实际案例。"
date: 2018-11-15T00:00:00+08:00
lastmod: 2018-12-02T07:46:38.000Z
url: "/2018/11/15/App Store上架漫谈/"
tags:
  - "iOS知识小结"
draft: false
---

## 前言

最近忙着写Bug😂，好久没有写文章了。今天和大家分享下我最近上架第二个独立开发的APP“识之”的上架经验（其实就是为了做一波广告）。

> 重点来了！！！
> 识之，人工智能AI识别，动物、植物、Logo、汽车车型、菜品、通用（识别各种东西）统统可以识别。只需用相机拍一张照片，或者从相册中选择要识别的图片，即可得到答案。使用完全免费使用，解决您的知识焦虑！
> 下载链接：http://t.cn/EAs5ubq
> 五星好评截图返现💕

好了，重点结束了，接下来聊点闲话😏。

## 聊聊审核

“识之”是我上架的第二个独立开发APP，2天搞定审核成功上架（第一个APP是3天），有些心得和大家分享下。
不得不说苹果审核团队现在的效率很高，一般一天就可以审核完成，我记得我刚开始做iOS那会，审核一次要一周，真的太漫长了。
每次提交新版本之后，第二天早上起床第一件事情就是收邮件。经常会看到这样的标题的邮件，心态瞬间蹦了。

![New Message from App Store](WechatIMG82.jpeg)

但是不要慌，这只是苹果怀疑你存在一些问题，并不代表真的有问题。先静下心来，读读这篇[上架过审秘籍](https://developer.apple.com/cn/app-store/review/guidelines)。

然后`仔细阅读`苹果的答复，仔细揣摩审核团队的用意。把审核团队当做小白用户，站在他们的角度来思考他们提出的问题，然后对照[苹果审核条例](https://developer.apple.com/cn/app-store/review/guidelines)仔细检查。如果确认自己不存在问题，就直接回复邮件说明，针对审核团队提出的问题详细解释（不需要重新提交二进制文件），一般隔天就能收到审核团队的答复。

> 这里有个技巧我屡试不爽，提交审核时，可以附上一个演示视频。因为APP的业务逻辑一般比较复杂，单靠文字描述难以表述清楚（想想产品经理当面交代的功能都经常被做偏，别说短短一封邮件了），而且长文本会让人看着很抓狂，审核团队一天密集的审核，看着长篇大论心情自然不好。这时候附上一个精心录制的演示视频，一眼就可以看懂你的APP是干嘛的。
> 视频推荐上传到Youtube方便国外观看。

如果确认APP真的存在问题，那就乖乖的修改吧，修改之后重新提交审核（额。。。马甲包什么的不在本文的讨论范围）。

> 今年10月后上架的APP都需要提供隐私政策，[这篇文章](http://crmo.github.io/2018/10/13/应对苹果隐私政策看我就够了/)教你轻松应对。

## 实际案例

这里和大家分享下“识之”的上架过程，”香蕉播放器“的上架过程看[这篇文章](http://crmo.github.io/2018/10/07/记“香蕉播放器”上架的辛酸历程/)。
提交的第二天就收到拒信，涉及到的条款：`3.1.4`、`4.2`（这次终于没有刺激的2.1大礼包了）。下面是审核团队的回复：

```
Guideline 3.1.4 - Business - Payments - Content Codes


Your app enables additional features or functionality when used with augmented reality markers or QR codes. However, those features are not available in the app to users without the necessary markers.

Next Steps

To resolve this issue, please provide a means to access these features from within the app, such as through achievements or in-app purchase. If they can be freely obtained, such as through a link to a website, please revise your app to include clear instructions for obtaining the necessary markers or codes.

Please note that apps cannot require users to purchase unrelated products or engage in advertising or marketing activities to unlock app functionality.

Guideline 4.2 - Design - Minimum Functionality

We noticed that your app includes an AR or QR scanner but does not include any additional content or functionality unless the user has access to the AR marker or QR code. While we understand that your app displays additional content when an AR marker or QR code is scanned, to users who do not have access to the AR markers or QR codes, your app only appears to display a camera view.

Next Steps

We encourage you to provide your users with additional content in your app, including directions on how to use your app and information on how to obtain any necessary AR markers or QR codes.

To ensure users have the best experience, apps should provide valuable utility or entertainment, draw people in by offering compelling capabilities or content, or enable people to do something they couldn't do before or in a way they couldn't do it before.
```

阅读理解时间开始了，第一遍看完我是一脸懵逼的，回复中提到了两个关键词`AR markers`和`QR codes`，可是我根本没有用到这些东西。于是我冷静下来，查了下审核指南。

![](15422845505208.jpg)

![](15422846190717.jpg)

结合审核指南就能理解审核团队的用意了，他们没有理解我的APP的功能，我的APP主要页面是一个相机，拍一张照片，然后识别图片中的物体是啥。
审核团队的理解是APP需要配合特殊的实体物体或者二维码才能正常使用，否则APP就没有任何用途。这显然是误解我了，于是我录制了一个视频，详细的演示了APP的功能，配上文字说明：

```
Dear Apple Review Team:
    Thank you for your patience review, we have done a detailed check on the following questions.
    Our app does not depend on specific markers or QR codes,users can use our app recognize anything,such as cars,plants,animals,dishes,logos.
    We made this app to help users identify objects around them.For example, if the user sees a beautiful plant and wants to know what it is,he can open our app，then take a photo use camera,our app will tell him what is this in the photo.
    We recorded a detailed demo video to illustrate our features:https://youtu.be/1okyq-ZJGzU
    Finally, thank you again for your hard review.
```

 
Dear Apple Review Team,

Thank you for your patience review, we have done a detailed check on the following questions.

First of all, you may have misunderstood. We do not use NFC function in the application.

Then we recorded a demonstration video of the app's features to showcase the main functions of our app, hoping it can assist you in completing the review.

Finally, I would like to explain that our main update this time is to update the display of holiday information for 2024. There are no other new features added. We hope to cooperate with you to complete the review work as soon as possible and present the latest information to users at an early date.

Thank you again for your hard review.