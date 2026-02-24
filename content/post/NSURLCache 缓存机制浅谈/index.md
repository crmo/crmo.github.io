---
title: "NSURLCache 缓存机制浅谈"
date: 2019-04-16T00:00:00+08:00
lastmod: 2019-04-16T12:48:12.000Z
url: "/2019/04/16/NSURLCache 缓存机制浅谈/"
tags:
  - "iOS知识小结"
draft: false
---

APP 中有很多从服务器获取数据、资源的需求，为了节省流量、加快访问速度、离线使用等需求，就会使用到网络缓存。`HTTP协议`对于缓存设计了很多机制，感兴趣的同学可以看看[《RFC2616-section13-Caching in HTTP》](https://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13)。

## iOS 中常见缓存机制

在iOS中，如果没有特殊需求，使用系统的缓存机制就可以满足。如：max-age、Last-Modified、ETag、Expires等机制系统都实现了的，不需要自己再去搞一套。只需要将 `NSURLRequest` 的 `cachePolicy` 设置为 `NSURLRequestUseProtocolCachePolicy` 。

```objc
NSURLRequest *request = [[NSURLRequest alloc] init];
request.cachePolicy = NSURLRequestUseProtocolCachePolicy;
```

这里简单说下常见的几种机制，首先来看一个`GET请求`的响应报文，里面包含了几种常见的缓存标识。

```
HTTP/1.1 200 
Cache-Control	max-age=86400, private
Last-Modified	Tue, 16 Apr 2019 06:07:39 GMT
ETag	W/"28111-1554979928000"
Expires	Wed, 17 Apr 2019 06:07:39 GMT
Date	Tue, 16 Apr 2019 06:07:39 GMT
Transfer-Encoding	chunked
Connection	keep-alive
```

### max-age

`max-age` 是 `cache-control` 下的一个指令，表示 `Response` 的最大 Age。例如：

> Cache-Control	 max-age=86400, private

含义为：该 `Response` 的有效期为1天，在一天以内，同样的 URL 将不会再次请求，直接使用缓存。

### Expires

`Expires` 告诉客户端 `Response` 的过期时间。例如：

> Expires Wed, 17 Apr 2019 06:07:39 GMT

含义为：该 `Response` 在 `Wed, 17 Apr 2019 06:07:39 GMT` 时过期，在这之前，同样的 URL 将不会再次请求，直接使用缓存。
需要注意的是，`max-age` 的优先级大于 `expires`。

### Last-Modified

`Last-Modified` 指明资源的最终修改时间，客户端在请求的时候，将这个值带在 `If-Modified-Since` 中。例如：

> If-Modified-Since	Thu, 11 Apr 2019 10:52:08 GMT

服务器会根据客户端传递的时间判断资源是否有更新，如果没有更新，服务器返回304，客户端直接使用缓存，如果有更新，服务器返回200和最新的资源。

### Etag

`Etag` 类似于资源的唯一hash值，资源发生变化，这个值就发生变更，客户端在请求资源时，会将 `Etag` 放在 `If-None-Match` 中，例如：

> If-None-Match 	W/"28111-1554979928000"

服务端根据客户端传递的 `Etag` 判断资源是否有更新，如果没有更新，服务器返回304，客户端直接使用缓存，如果有更新，服务器返回200和最新的资源。

## 启发式缓存（heuristic expiration）

在测试缓存机制时，发现了一种特殊情况，返回报文里没有 `max-age` 和 `Expires`，再次请求相同URL时却直接使用的缓存，没有重新发请求，请求报文如下：

```
HTTP/1.1 200 
Accept-Ranges	bytes
ETag	W/"28111-1554979928000"
Last-Modified	Thu, 11 Apr 2019 10:52:08 GMT
Date	Tue, 16 Apr 2019 07:23:21 GMT
Content-Type	image/jpeg
Content-Length	28111
Connection	keep-alive
```

让人摸不着头脑，在查询资料后发现一篇文章，提到了这个现象，[Caching and NSURLConnection](https://blackpixel.com/writing/2012/05/caching-and-nsurlconnection.html)。

在文章的指引下，仔细研究了下[RFC2616-section13-Caching in HTTP](https://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13)，发现了答案。

RFC的原文如下：

> If none of Expires, Cache-Control: max-age, or Cache-Control: s- maxage (see section 14.9.3) appears in the response, and the response does not include other restrictions on caching, the cache MAY compute a freshness lifetime using a heuristic. The cache MUST attach Warning 113 to any response whose age is more than 24 hours if such warning has not already been added.
> Also, if the response does have a Last-Modified time, the heuristic expiration value SHOULD be no more than some fraction of the interval since that time. A typical setting of this fraction might be 10%.

这是一种叫启发式缓存（heuristic expiration）的策略，在 response 中如果没有 Expires、max-age、s-maxage，来明确指定资源的过期时间，NSURLCache 会根据 Last-Modified 来计算一个过期时间。

> 根据实验结果，在iOS中计算公式是这样的：lifetime = (Last-Modified - Now) * 10%


## 参考文章

1、[Caching and NSURLConnection](https://blackpixel.com/writing/2012/05/caching-and-nsurlconnection.html)
2、[RFC2616-section13-Caching in HTTP](https://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13)
3、[NSURLCache-NSHipster](https://nshipster.com/nsurlcache/)
4、[iOS网络缓存扫盲篇 - 使用两行代码就能完成80%的缓存需求](https://segmentfault.com/a/1190000004356632)