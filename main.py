import requests
from bs4 import BeautifulSoup

resp = requests.get('https://blog.castman.net/web-crawler-tutorial/ch2/blog/blog.html')
soup = BeautifulSoup(resp.text,'html.parser')

print(soup.find('h4'))
print(soup.h4.a.text)

main_titles = soup.find_all('h4')
for title in main_titles:
    print(title.a.text)



