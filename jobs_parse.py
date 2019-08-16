# -*- coding: utf-8 -*-

import sqlite3
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

conn = sqlite3.connect('vacancies.sqlite')
cursor = conn.cursor()

def ask_user(text):
    ans = ''
    while ans not in ['y', 'n']:
        ans = input(text)
    return ans
    
ans = ask_user('Создать новую таблицу? (y/n): ')
if ans == 'y':
    cursor.execute('DROP TABLE IF EXISTS vacancies')
    conn.commit()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS vacancies (
        url TEXT PRIMARY KEY,
        title TEXT,
        company TEXT,
        street TEXT,
        salary TEXT DEFAULT NULL,
        experience TEXT DEFAULT NULL,
        work_regime TEXT DEFAULT NULL,
        descr TEXT DEFAULT NULL,
        key_skills TEXT DEFAULT NULL,
        creation_date TEXT DEFAULT NULL,
        partner TEXT,
        date_updated DATE DEFAULT CURRENT_DATE,
        visited BOOLEAN DEFAULT FALSE)''')
conn.commit()

def insert_vacancy(data):
    try:
        cursor.execute('''
            INSERT INTO vacancies (url, title, company, street, partner)
            VALUES (?, ?, ?, ?, ?)''', data)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        cursor.execute('''
            UPDATE vacancies SET date_updated=CURRENT_DATE WHERE url=:url
        ''', {'url': data[0]})
        conn.commit()

def update_vacancy(url, salary, experience, work_regime, 
                   descr, key_skills, creation_date):
    cursor.execute('''
        UPDATE vacancies SET salary=:salary, experience=:exp, work_regime=:wr,
            descr=:descr, key_skills=:ks, creation_date=:cd, visited=TRUE
        WHERE url=:url
        ''', {'url': url, 'salary': salary, 
              'exp': experience, 'wr': work_regime, 
              'descr': descr, 'ks': key_skills, 'cd': creation_date})
    conn.commit()

def parse_trud(url):
    driver.get(url)

    divs = driver.find_elements_by_css_selector('div[class*=number]')

    counter = 0
    for div in divs:
        a = div.find_element_by_css_selector('a')
        title = a.text
        href = a.get_attribute('href')
        partner = a.get_attribute('partner')
        company = div.find_element_by_class_name('institution').text
        street = div.find_element_by_class_name('geo-location').text
        
        insert_vacancy((href, title, company, street, partner))
        
        counter += 1
    return counter

def parse_partner(url, partner):
    if partner == 'hh.ru':
        return parse_hh(url)
    elif partner == 'talents.yandex.ru':
        return parse_yandex(url)
    elif partner.startswith('superjob.ru'):
        return parse_superjob(url)        

def parse_hh(url):
    salary = driver.find_element_by_class_name('vacancy-salary').text
    
    experience = driver.find_element_by_css_selector(
        '[data-qa=vacancy-experience]'
    ).text
    work_regime = driver.find_element_by_css_selector(
        '[data-qa=vacancy-view-employment-mode]'
    ).text
    descr = driver.find_element_by_css_selector(
        'div[data-qa=vacancy-description'
    ).text
    skills = driver.find_elements_by_css_selector(
        '[data-qa=skills-element]'
    )
    creation_date = driver.find_element_by_class_name(
        'vacancy-creation-time'
    ).text
            
    key_skills = []
    for skill in skills:
        key_skills.append(skill.text)
    s_key_skills = ', '.join(key_skills)
    
    return salary, experience, work_regime, descr, s_key_skills, creation_date
        
def parse_superjob(url):
    try:
        salary = driver.find_element_by_class_name('PlM3e')
        salary = salary.text
    except NoSuchElementException:
        salary = 'Не указано'
        
    text = driver.find_element_by_css_selector('._3AQrx + div').text
    parts = text.split(', ', 1)
    
    experience = 'Не указано'
    work_regime = text
    key_skills = ''

    if parts[0].startswith('Опыт работы'):
        experience = parts[0]
        work_regime = parts[1]
    
    descr = driver.find_element_by_class_name('_2LeqZ').text
    creation_date = driver.find_element_by_css_selector(
        'div._2g1F- + div > span._9fXTd'
    ).text
            
    return salary, experience, work_regime, descr, key_skills, creation_date
    
def parse_yandex(url):
    experience = 'Не указано'
    schedule = driver.find_element_by_class_name('tag_icon_schedule').text
    employment = driver.find_element_by_class_name('tag_icon_employment').text
    work_regime = employment + ', ' + schedule + ' график'
    key_skills = ''
    descr = driver.find_element_by_class_name('vacancy-description').text
    creation_date = ''
    
    return experience, work_regime, descr, key_skills, creation_date

    
base_url = 'https://trud.com/search/search.html?'
company = str(0)
city = 'Новосибирск'
show = 'jobs'
query = 'Разработчик'

print('Текущий запрос: город - {}, профессия - {}'.format(city, query))
ans = ask_user('Изменить? (y/n): ')

if ans == 'y':
    ans = ''
    while ans != 'y':
        city = input('Введите город: ')
        query = input('Введите профессию: ')
        print('Текущий запрос: город - {}, профессия - {}'.format(city, query))
        ans = ask_user('Верно? (y/n): ')

url = '&'.join([base_url + 'company='+company, 
                'show=' + show,
                'query=' + query,
                'city=' + city])

driver = webdriver.Firefox()
# driver = webdriver.Chrome()
driver.implicitly_wait(10)

page = 1

while True:
    counter = parse_trud(url)
    print('{} вакансий добавлено в таблицу'.format(counter))
    
    ans = ask_user('Продолжить? (y/n): ')
    if ans == 'n':
        break
    
    page += 1
    url = driver.current_url + 'page/' + str(page)

href_to_visit = None

query = 'SELECT url, partner FROM vacancies WHERE visited=FALSE'
cursor.execute(query)
result = cursor.fetchone()
if result is not None:
    href_to_visit, partner = result

while href_to_visit is not None:
    driver.get(href_to_visit)
    vacancy_info = parse_partner(href_to_visit, partner)    
    update_vacancy(href_to_visit, *vacancy_info)
    cursor.execute(query)
    result = cursor.fetchone()
    if result is not None:
        href_to_visit, partner = result
    else:
        href_to_visit = None

driver.quit()
conn.close()
