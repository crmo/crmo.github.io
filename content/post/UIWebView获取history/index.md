---
title: "UIWebView获取详细浏览记录"
date: 2018-08-01T00:00:00+08:00
lastmod: 2018-10-07T08:13:37.000Z
url: "/2018/08/01/UIWebView获取history/"
tags:
  - "iOS知识小结"
draft: false
---

> 2018.8.1

## 需求

获取`UIWebView`的前进后退的浏览记录，举个例子，比如从A->B->C->B，此时B上一页是A，下一页是C，需要获取A、C的URL信息。

> WKWebView暴露了这个属性，`WKBackForwardList *backForwardList`。可以很容易的取到，无奈项目还是使用的`UIWebView`，于是有了后面的探索。

首先在`UIWebView`提供的API里找，相关的API只有`canGoBack`和`canGoForward`，命名很直观，是否可以后退和前进，这条路走不通。
想到是否可以通过JS的Window.history获取到，查了下API，唯一一个有点像的`length`属性，智能取到浏览记录中的所有URL的数量，不区分前后，比如在上面提到的例子中，在B页面取到的`length`是3，而且不能取出具体的URL。

![](15325235986699.jpg)



无奈只有上源码了，我下载的是[“WebKit-7604.1.38.0.7”和“WebCore-7604.1.38.0.7”](https://opensource.apple.com/release/ios-110.html)。

## Window.History.length实现本质

在WebCore里面找到了JS方法`Window.History.length`实现的本质，上代码：

```c
// WebCore History.cpp
unsigned History::length() const
{
    if (!m_frame)
        return 0;
    auto* page = m_frame->page();
    if (!page)
        return 0;
    return page->backForward().count();
}
```

```c
// WebCore BackForwardController.cpp
int BackForwardController::count() const
{
    // count = 当前页之前的页面总数 + 当前页之后的页面总数 + 1
    return m_client->backListCount() + 1 + m_client->forwardListCount();
}
```

在`WebCore`里面`backListCount()`、`forwardListCount()`定义是虚函数，具体实现在`WebKit`可以找到。

```c
// WebKit BackForwardList.mm
int BackForwardList::backListCount()
{
    return m_current == NoCurrentItemIndex ? 0 : m_current;
}

int BackForwardList::forwardListCount()
{
    return m_current == NoCurrentItemIndex ? 0 : (int)m_entries.size() - (m_current + 1);
}
```

还有一个方法我们需要关注一下，后面会用到。

```c
// WebKit BackForwardList.mm
// 获取之前最多几条历史记录
void BackForwardList::backListWithLimit(int limit, Vector<Ref<HistoryItem>>& list)
{
    list.clear();
    if (m_current != NoCurrentItemIndex) {
        unsigned first = std::max(static_cast<int>(m_current) - limit, 0);
        for (; first < m_current; ++first)
            list.append(m_entries[first].get());
    }
}
```

## 获取History

在`WebView`的中，我们可以找到`WebBackForwardList`的定义。

```objectivec
/*!
    @property backForwardList
    @abstract The backforward list for this WebView.
*/    
@property (nonatomic, readonly, strong) WebBackForwardList *backForwardList;
```

`WebBackForwardList`是对`BackForwardList`的一层封装，阅读一下它的.h文件，不难找到获取浏览记录的方法。

```objective-c
/*!
    @method backListWithLimit:
    @abstract Returns a portion of the list before the current entry.
    @param limit A cap on the size of the array returned.
    @result An array of items before the current entry, or nil if there are none.  The entries are in the order that they were originally visited.
*/
- (NSArray *)backListWithLimit:(int)limit;
```

上面的方法可以获取到一个`WebHistoryItem`数组，`WebHistoryItem`保存了浏览记录的详细信息。

## 获取WebBackForwardList

`UIWebView`没有暴露获取`WebView`或者`WebBackForwardList`的方法，但是我们可以用KVO曲线救国，于是我们需要找到`WebView`的私有变量名。用runtime可以做到，为了简化这个过程，我写了一个工具类来辅助搜索，具体可以看[这篇文章-runtime实现私有变量搜索](https://crmo.github.io/2018/07/31/runtime实现私有变量搜索/)。简单来说就是用runtime获取类成员变量列表，然后用BFS来搜索我们要找的类。


```objectivec
// 以UIWebView为根节点，BFS搜索WebView
[BFSSearchClass searchClass:@"WebView" inClass:@"UIWebView"];

// 搜索结果如下
// Class Name：类名，Ivar Name：变量名，Super Class：父类
Class Name:【WebView】,Ivar Name:【_webView】
Class Name:【UIWebDocumentView】,Ivar Name:【Super Class】
Class Name:【UIWebBrowserView】,Ivar Name:【browserView】
Class Name:【UIWebViewInternal】,Ivar Name:【_internal】
Root Class:UIWebView
```

有了上面的结论，我们就可以用KVC来获取到浏览记录了。

```objectivec
- (void)printWebViewHistory:(UIWebView *)aWebView {
    id webviewInternal = [aWebView valueForKey:@"_internal"];
    id browserView = [webviewInternal valueForKey:@"browserView"];
    id webView = [browserView valueForKey:@"_webView"];
    id backForwardList = [webView performSelector:@selector(backForwardList)];
    // WebHistoryItem存储的具体某条浏览记录信息
    NSArray *historyItems = [backForwardList performSelector:@selector(backListWithLimit:) withObject:@10];
    for (id item in historyItems) {
        // 获取浏览记录的url 
        NSString *url = [item performSelector:@selector(URLString)];
        NSLog(@"%@", url);
    }
}
```