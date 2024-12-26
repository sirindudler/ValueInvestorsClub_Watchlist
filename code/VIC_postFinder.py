import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
from datetime import datetime

class VICPostFinder:
    def __init__(self, headless=True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.add_cookies()
        self.wait = WebDriverWait(self.driver, 20)

        # Delay settings (to avoid overloading the server)
        self.base_delay = random.uniform(8, 12)  # Base delay between requests
        self.jitter = 4  # Random jitter added to base delay
        self.consecutive_requests = 0  # Track number of requests
        self.max_consecutive = 5  # Max requests before longer delay

    def add_cookies(self):
        cookies = [
        {
            'name': 'vic_session',
            'value': 'YOUR_SESSION_COOKIE_VALUE',
            'domain': '.valueinvestorsclub.com'
        }
    ]
    
        # First visit the site
        self.driver.get('https://valueinvestorsclub.com')
    
        # Then add the cookies
        for cookie in cookies:
            self.driver.add_cookie(cookie)

    def smart_delay(self):
        self.consecutive_requests += 1
        
        # Add longer delay every few requests
        if self.consecutive_requests >= self.max_consecutive:
            delay = random.uniform(60, 90)  # Longer 1-1.5 minute delay
            self.consecutive_requests = 0  # Reset counter
        else:
            delay = self.base_delay + random.uniform(0, self.jitter)
        
        time.sleep(delay)

    def read_member_list(self, csv_path):
        with open(csv_path, 'r') as file:
            lines = file.readlines()
        
        members = []
        for line in lines:
            if line.strip():  # Skip empty lines
                # Split at first space to separate username and description
                parts = line.strip().split(' ', 1)
                if len(parts) >= 1:
                    username = parts[0].strip('– ')  # Remove potential dash
                    members.append(username)
        
        return members

    def search_member(self, member_name):
        try:
            search_url = f"https://valueinvestorsclub.com/search/{member_name}"
            self.driver.get(search_url)
            self.smart_delay()
            
            # Click on member link
            member_link = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '/html/body/div[2]/table[1]/tbody/tr[2]/td/div/div/a'))
            )
            member_link.click()
            self.smart_delay()
            
            # Find the ideas table
            table = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table.itable.box-shadow"))
            )
            
            # Find all post rows (skip header row)
            rows = table.find_elements(By.TAG_NAME, "tr")[1:]
            
            posts = []
            for row in rows:
                try:
                    # Get columns from the row
                    cols = row.find_elements(By.CLASS_NAME, "col-xs-12")
                    
                    if len(cols) >= 2:
                    # Extract just title, ticker, and date
                        title_div = cols[0].find_element(By.CLASS_NAME, "vich1")
                        title_element = cols[0].find_element(By.TAG_NAME, "a")
                        title = title_element.text
                        ticker = cols[0].text.split()[-1]
                        date = cols[1].text.strip()
                        url = title_element.get_attribute("href")

                        # Extract ticker, excluding S and W tags
                        text_parts = title_div.text.split()
                        ticker = ""
                        if text_parts:
                            last_word = text_parts[-1]
                            if last_word not in ['S', 'W']:
                                ticker = last_word
                        
                        date = cols[1].text.strip()
                    
                    posts.append({
                        'member': member_name,
                        'title': title,
                        'ticker': ticker,
                        'date': date,
                        'url': url
                    })
                    
                except Exception as e:
                    print(f"Error processing row: {str(e)}")
                    continue
                    
            return posts
            
        except Exception as e:
            print(f"Error searching for member {member_name}: {str(e)}")
            return None

    def process_member_list(self, csv_path, output_path):
        member_names = self.read_member_list(csv_path)
        
        all_posts = []
        for member_name in member_names:
            posts = self.search_member(member_name)
            if posts:
                all_posts.extend(posts)
            # Extra delay between members
            time.sleep(random.uniform(2, 7))
        
        # Create DataFrame and rename columns
        results_df = pd.DataFrame(all_posts)
        results_df = results_df.rename(columns={
            'date': 'date',
            'ticker': 'ticker',
            'member': 'author',
            'title': 'title',
            'url': 'url'
        })
        
        # Convert date to datetime for sorting
        results_df['date'] = pd.to_datetime(results_df['date'], format='%b %d, %Y')
        
        # Sort by date descending
        results_df = results_df.sort_values('date', ascending=False)
        
        # Convert date back to string format if needed
        results_df['date'] = results_df['date'].dt.strftime('%Y-%m-%d')
        
        # Reorder columns
        ordered_columns = ['date', 'ticker', 'author', 'title', 'url']
        results_df = results_df[ordered_columns]

        # Add scrape date to filename
        scrape_date = datetime.now().strftime('%Y_%m_%d')
        # Format to YYYY/MM/DD
        scrape_date = scrape_date[:4] + '_' + scrape_date[4:6] + '_' + scrape_date[6:]
        output_path = output_path.replace('.csv', f'_{scrape_date}.csv')
        
        # Save to CSV
        results_df.to_csv(output_path, index=False)
        print(f"Results saved to {output_path}")

    def close(self):
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    scraper = VICPostFinder(headless=True)
    try:
        scraper.process_member_list('data/VIC_Members.csv', 'results/vic_posts.csv')
    finally:
        scraper.close()