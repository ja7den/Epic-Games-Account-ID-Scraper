from pycurl import Curl, URL, CUSTOMREQUEST, HTTPHEADER, POSTFIELDS, SSL_VERIFYHOST, SSL_VERIFYPEER, TIMEOUT
from threading import Thread, Lock
from queue import Queue

import json

BEARER_TOKEN_AUTHORIZATION = "Basic eHl6YTc4OTFwNUQ3czlSNkdtNm1vVEhXR2xvZXJwN0I6S25oMThkdTROVmxGcyszdVErWlBwRENWdG8wV1lmNHlYUDgrT2N3VnQxbw=="
ACCESS_TOKEN_AUTHORIZATION = "Basic MzQ0NmNkNzI2OTRjNGE0NDg1ZDgxYjc3YWRiYjIxNDE6OTIwOWQ0YTVlMjVhNDU3ZmI5YjA3NDg5ZDMxM2I0MWE="

ROCKET_LEAGUE_USER_AGENT = "EOS-SDK/1.13.0-17835668 (Windows/10.0.19041.1348.64bit) Rocket League/211123.48895.355454"
EPIC_GAMES_CONTENT_TYPE = "application/x-www-form-urlencoded; charset=UTF-8"

INFO = "[\x1b[31m+\x1b[39m]"

class Signatures(object):
    def __init__(self) -> None:
        super(Signatures, self).__init__()
        
    def generate_access_token(self, curl: Curl, webcode: str) -> str:        
        curl.setopt(CUSTOMREQUEST, "POST")
        curl.setopt(URL, "https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token")
        
        curl.setopt(HTTPHEADER, ["Authorization:" + ACCESS_TOKEN_AUTHORIZATION, "Content-Type: " + EPIC_GAMES_CONTENT_TYPE])
        curl.setopt(POSTFIELDS, "grant_type=authorization_code&code=" + webcode)
       
        curl.setopt(SSL_VERIFYHOST, 0)
        curl.setopt(SSL_VERIFYPEER, 0)

        response = curl.perform_rs()

        if "access_token" not in response:
            print("{} Failed to obtain 'Access Token'".format(INFO))
            exit(0)
        return json.loads(response)["access_token"]

    def generate_exchange_token(self, curl: Curl, access_token: str) -> str:        
        curl.setopt(CUSTOMREQUEST, "GET")
        curl.setopt(URL, "https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/exchange")

        curl.setopt(HTTPHEADER, ["Authorization: Bearer " + access_token])
       
        curl.setopt(SSL_VERIFYHOST, 0)
        curl.setopt(SSL_VERIFYPEER, 0)
        
        response = curl.perform_rs()

        if "code" not in response:
            print("{} Failed to obtain 'Exchange Token'".format(INFO))
            exit(0)
        return json.loads(curl.perform_rs())["code"]

    def generate_bearer_token(self, curl: Curl, exchange_token: str) -> str:
        curl.setopt(CUSTOMREQUEST, "POST")
        curl.setopt(URL, "https://api.epicgames.dev/epic/oauth/v1/token")

        curl.setopt(HTTPHEADER, ["Authorization: " + BEARER_TOKEN_AUTHORIZATION, "Content-Type: " + EPIC_GAMES_CONTENT_TYPE, "User-Agent: " + ROCKET_LEAGUE_USER_AGENT])
        curl.setopt(POSTFIELDS, "grant_type=exchange_code&exchange_code=" + exchange_token)

        curl.setopt(SSL_VERIFYHOST, 0)
        curl.setopt(SSL_VERIFYPEER, 0)

        response = curl.perform_rs()

        if "access_token" not in response:
            print("{} Failed to obtain 'Bearer Token'".format(INFO))
            exit(0)
        return json.loads(response)["access_token"]

    def generate_tokens(self, webcode: str) -> str:
        return self.generate_bearer_token(Curl(), self.generate_exchange_token(Curl(), self.generate_access_token(Curl(), webcode)))

class Scraper(object):
    def __init__(self) -> None:
        super(Scraper, self).__init__()
        self.usernames = open("usernames.txt", "r").read().splitlines()
        self.signature, self.queue = Signatures(), Queue()
        self.webcode, self.bearer, self.run = None, None, True

    def new_file(self, array: list, file_name: str) -> None:
        file = open(file_name, "w+")
        for line in array:
            file.write(line + "\n")
        return file.close()

    def write_file(self, content: str, file_name: str) -> None:
        file = open(file_name, "a+")
        file.write(content + "\n")
        return file.close()

    def load_auth(self, webcode):
        self.bearer = self.signature.generate_tokens(webcode)

    def load_usernames(self):
        for username in self.usernames:
            self.queue.put(username)
        return

    def get_account_id(self, username: str) -> str:
        try:
            curl = Curl()
            curl.setopt(URL, "https://api.epicgames.dev/epic/id/v1/accounts?displayName=" + username)
            curl.setopt(HTTPHEADER, ["Authorization: Bearer " + self.bearer, "Connection: keep-alive", "Accept-Encoding: gzip"])

            curl.setopt(SSL_VERIFYHOST, 0)
            curl.setopt(SSL_VERIFYPEER, 0)
            curl.setopt(TIMEOUT, 10)

            response = curl.perform_rs()
            if username in response.lower():
                return json.loads(response)[0]["accountId"]
            return None
        except: 
            Curl()
            pass

    def run_scraper(self):
        while self.run:
            username = self.queue.get()
            account_id = self.get_account_id(username)

            if not account_id:
                print("{} Username: {} | Voided".format(INFO, username))
                self.write_file(username, "voided.txt")
            else:
                print("{} Username: {} | Account ID: {}".format(INFO, username, account_id))
                self.write_file(username+":"+account_id, "scraped.txt")
            
            self.usernames.remove(username)
            self.new_file(self.usernames, "usernames.txt")

            if self.queue.empty():
                self.run = False

def main():
    init = Scraper()
    init.load_usernames()

    print("{} Epic Games Account ID Scraper | version 1.0\n".format(INFO))
    webcode = input("{} Webcode: ".format(INFO))

    init.load_auth(webcode)
    print("{} Bearer Token generated!\n".format(INFO))

    threads = input("{} Threads: ".format(INFO))
    print("")

    for i in range(int(threads)):
        t = Thread(target = init.run_scraper)
        #t.setDaemon(True)
        t.start()

    while True:
        if not init.run:
            print("{} Finished scraping {} usernames".format(INFO, len(init.usernames)))
            exit(0)

if __name__ == "__main__":
    main()
