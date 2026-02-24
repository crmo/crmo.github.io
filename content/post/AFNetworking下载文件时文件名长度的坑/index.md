---
title: "AFNetworking下载文件时文件名长度的坑"
date: 2018-03-29T22:23:00+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2018/03/29/AFNetworking下载文件时文件名长度的坑/"
tags:
  - "iOS知识小结"
draft: false
---

## 背景

最近遇到一个Bug，在用AFNetworking下载文件的时候莫名其妙的失败了，跟了一下发现一个小坑，记录一下防止以后再掉进去。
> iOS和Linux的文件名的长度限制相同都是255个字符！！！

问题根源是文件名超度超过了255个字符，AFNetworking下载文件是成功了（框架会把文件下载到一个临时文件，例如：`CFNetworkDownload_xxx.tmp`，这个文件名不会出现过长的问题），下载成功之后会copy到调用者指定路径，在这里指定的文件名超过了255个字符，导致创建文件失败，于是回调是成功了，但是在设置的路径找不到这个文件。

上代码！

下载代码：

```
// 注意对文件名长度进行处理！！！
NSString *destination = @"下载地址（长度大于255）";
NSURLSessionDownloadTask *aTask = [self.updownloadSessionManager downloadTaskWithRequest:mutableRequest progress:^(NSProgress * _Nonnull downloadProgress) {
        
    } destination:^NSURL * _Nonnull(NSURL * _Nonnull targetPath, NSURLResponse * _Nonnull response) {
        return [NSURL fileURLWithPath:destination];
    } completionHandler:^(NSURLResponse * _Nonnull response, NSURL * _Nullable filePath, NSError * _Nullable error) {
        // 下载成功后会回调该block，但是路径`destination`找不到这个文件
    }];
    [aTask resume];
```

出错的地方**AFURLSessionManager.m**

```
- (void)URLSession:(NSURLSession *)session
      downloadTask:(NSURLSessionDownloadTask *)downloadTask
didFinishDownloadingToURL:(NSURL *)location
{
    self.downloadFileURL = nil;

    if (self.downloadTaskDidFinishDownloading) {
        self.downloadFileURL = self.downloadTaskDidFinishDownloading(session, downloadTask, location);
        if (self.downloadFileURL) {
            NSError *fileManagerError = nil;

            // location是临时文件，是下载成功了
            // self.downloadFileURL 是目标路径，文件名超过255
            // 移动文件会报错
            if (![[NSFileManager defaultManager] moveItemAtURL:location toURL:self.downloadFileURL error:&fileManagerError]) {
            // 出错会发通知，可以监听处理
                [[NSNotificationCenter defaultCenter] postNotificationName:AFURLSessionDownloadTaskDidFailToMoveFileNotification object:downloadTask userInfo:fileManagerError.userInfo];
            }
        }
    }
}
```

我们来看看`AFURLSessionDownloadTaskDidFailToMoveFileNotification`的定义
**AFURLSessionManager.h**

```
/**
 Posted when a session download task encountered an error when moving the temporary download file to a specified destination.
 */
FOUNDATION_EXPORT NSString * const AFURLSessionDownloadTaskDidFailToMoveFileNotification;
```


