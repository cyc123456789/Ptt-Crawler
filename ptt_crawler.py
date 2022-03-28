import json
import re
import requests
from bs4 import BeautifulSoup
from six import u

PTT_URL = 'https://www.ptt.cc'


def get_web_page(url):
    resp = requests.get(url=url,
                        cookies={'over18': '1'})
    if resp.status_code != 200:
        print('Invalid url:', resp.url)
        return None
    else:
        return resp.text


def get_articles(dom):
    soup = BeautifulSoup(dom, 'html.parser')
    # print(dom)
    # 上頁
    paging_div = soup.find('div', 'btn-group btn-group-paging')
    prev_url = paging_div.find_all('a')[1]['href']
    # print('Prev url:',prev_url)

    articles = []
    divs = soup.find_all('div', 'r-ent')
    # print([d.text for d in divs ])
    for d in divs:

        # if '[食記]' in d.find('div',class_='title').text.strip():
        # if d.find('div', class_='date').text.strip() == date:

        push_count = 0
        push_str = d.find('div', 'nrec').text
        if push_str:
            try:
                push_count = int(push_str)
            except ValueError:

                if push_str == '爆':
                    push_count = 99
                elif push_str.startswith('X'):
                    push_count = -10

        if d.find('a'):
            href = d.find('a')['href']
            title = d.find('a').text
            date = d.find('div', class_='date').text.strip()
            author = d.find('div', 'author').text if d.find('div', 'author') else ''
            articles.append({
                'date': date,
                'title': title,
                'href': href,
                'push_count': push_count,
                'author': author
            })

    return articles, prev_url


def get_author_ids(posts, pattern):
    ids = set()
    for post in posts:
        if pattern in post['author']:
            ids.add(post['author'])
    return ids


def get_articles_detail(link):
    single_page = get_web_page(link)

    soup = BeautifulSoup(single_page, 'html.parser')
    main_content = soup.find(id="main-content")
    metas = main_content.select('div.article-metaline')
    author = ''
    title = ''
    date = ''
    article_id = re.sub('\.html', '', link.split('/')[-1])
    board = main_content.select('div.article-metaline-right')[0].find(class_='article-meta-value').text
    if metas:
        author = metas[0].select('span.article-meta-value')[0].string if metas[0].select('span.article-meta-value')[
            0] else author
        title = metas[1].select('span.article-meta-value')[0].string if metas[1].select('span.article-meta-value')[
            0] else title
        date = metas[2].select('span.article-meta-value')[0].string if metas[2].select('span.article-meta-value')[
            0] else date

        # remove meta nodes
        for meta in metas:
            meta.extract()
        for meta in main_content.select('div.article-metaline-right'):
            meta.extract()

    # remove and keep push nodes
    pushes = main_content.find_all('div', class_='push')
    for push in pushes:
        push.extract()

    try:
        ip = main_content.find(text=re.compile(u'※ 發信站:'))
        ip = re.search('[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*', ip).group()
    except:
        ip = "None"

    # 移除 '※ 發信站:' (starts with u'\u203b'), '◆ From:' (starts with u'\u25c6'), 空行及多餘空白
    # 保留英數字, 中文及中文標點, 網址, 部分特殊符號
    filtered = [v for v in main_content.stripped_strings if v[0] not in [u'※', u'◆'] and v[:2] not in [u'--']]
    expr = re.compile(
        u(r'[^\u4e00-\u9fa5\u3002\uff1b\uff0c\uff1a\u201c\u201d\uff08\uff09\u3001\uff1f\u300a\u300b\s\w:/-_.?~%()]'))
    for i in range(len(filtered)):
        filtered[i] = re.sub(expr, '', filtered[i])

    filtered = [_f for _f in filtered if _f]  # remove empty strings
    # filtered = [x for x in filtered if article_id not in x]  # remove last line containing the url of the article
    content = ' '.join(filtered)
    content = re.sub(r'(\s)+', ' ', content)
    # print 'content', content

    # push messages
    p, b, n = 0, 0, 0
    messages = []
    for push in pushes:
        if not push.find('span', 'push-tag'):
            continue
        push_tag = push.find('span', 'push-tag').string.strip(' \t\n\r')
        push_userid = push.find('span', 'push-userid').string.strip(' \t\n\r')
        # if find is None: find().strings -> list -> ' '.join; else the current way
        push_content = push.find('span', 'push-content').strings
        push_content = ' '.join(push_content)[1:].strip(' \t\n\r')  # remove ':'
        push_ipdatetime = push.find('span', 'push-ipdatetime').string.strip(' \t\n\r')
        messages.append({'push_tag': push_tag, 'push_userid': push_userid, 'push_content': push_content,
                         'push_ipdatetime': push_ipdatetime})
        if push_tag == u'推':
            p += 1
        elif push_tag == u'噓':
            b += 1
        else:
            n += 1

    # count: 推噓文相抵後的數量; all: 推文總數
    message_count = {'all': p + b + n, 'count': p - b, 'push': p, 'boo': b, "neutral": n}

    # print 'msgs', messages
    # print 'mscounts', message_count

    # json data
    data = []
    data.append({
        'url': link,
        'board': board,
        'article_id': article_id,
        'article_title': title,
        'author': author,
        'date': date,
        'content': content,
        'ip': ip,
        'message_count': message_count,
        'messages': messages
    })
    # print 'original:', d

    return data


if __name__ == '__main__':
    current_page = get_web_page(PTT_URL + '/bbs/Food/index.html')
    articles = []
    detail_articles = []
    if current_page:
        page_count = 0
        # 抓幾頁
        page_max = 1
        current_articles, prev_url = get_articles(current_page)

        while current_articles and (page_count < page_max):
            # print('Round:', page_count)
            articles += current_articles
            current_page = get_web_page(PTT_URL + prev_url)
            current_articles, prev_url = get_articles(current_page)
            page_count = page_count + 1
            # print('Next Round:', page_count)

        # print(get_author_ids(articles, '5566'))
        print('有', len(articles), '篇文章')
        for a in articles:
            # if int(a['push_count']) > threshold:
            print(a)
        with open('title.json', 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, sort_keys=True, ensure_ascii=False)

        # TODO: 抓文章內容
    if articles:
        for a in articles:
            link = PTT_URL + a['href']
            print(link)
            current_detail_articles = get_articles_detail(link)
            detail_articles += current_detail_articles
        with open('detail_articles.json', 'w', encoding='utf-8') as f:
            json.dump(detail_articles, f, indent=2, sort_keys=True, ensure_ascii=False)
