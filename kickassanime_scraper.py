import re
import json
import asyncio
from async_web import fetch
from aiohttp import ClientSession
from anime_pace_scraperasdf import scraper
import os
from aiodownloader import downloader, utils
from typing import Tuple
from base64 import b64decode

class kickass:
    def __init__(
        self,
        session,
        url="https://www2.kickassanime.rs/anime/dummy",
        arbitrary_name=False,
        episode_link=None,
    ):
        if "episode" not in url.split("/")[-1]:
            self.base_url = url
        else:
            self.base_url = "/".join(url.split("/")[:-1])
        if arbitrary_name:
            self.name = "anything"
        else:
            self.name = " ".join(self.base_url.split("/")[-1].split("-")[:-1])
        self.episode_link = episode_link
        self.session = session

    @staticmethod
    async def _get_data(script):
        result = re.findall(r"\{.+\}", str(script))
        a = result[0].replace(r" || {}", "")
        return json.loads(a)

    async def scrape_episodes(self) -> GeneratorExit:
        soup = await fetch(self.base_url, self.session)
        for i in soup.find_all("script"):
            if "appUrl" in str(i):
                data = await kickass._get_data(i)
                # print(data.keys())
                results = data["anime"]["episodes"]
        self.last_episode = int(results[0]["slug"].split("/")[-1].split("-")[1])
        return ("https://www2.kickassanime.rs" + i["slug"] for i in results)

    async def get_embeds(self, episode_link=None) -> dict:
        """ player, download, ep_num, ext_servers, episode_countdown """
        if episode_link == None:
            if self.episode_link == None:
                raise Exception("no url supplied")
            else:
                pass
        else:
            self.episode_link = episode_link
        episode_num = int(self.episode_link.split("/")[-1].split("-")[1])
        print(f"Getting episode {episode_num}")
        soup = await fetch(self.episode_link, self.session)
        for i in soup.find_all("script"):
            if "appUrl" in str(i):
                data = await kickass._get_data(i)
                break

        result = []
        # for i,j in data["episode"].items():
        #     print(i,j)
        for i in data["episode"].values():
            try:
                if "http" in i:
                    result.append(i)
            except TypeError:
                pass
        # print(result)
        ret = {
            "player": [],
            "download": None,
            "ext_servers": None,
            "can_download": True,
            "episode_countdown": False,
        }
        for i in result:
            if "mobile2" in i.split("/"):
                # print('yes')
                ret["download"] = i.strip()
            else:
                # print('no')
                ret["player"].append(i.strip())
        try:
            if data["ext_servers"] != None:
                ret["ext_servers"] = data["ext_servers"]
            else:
                pass
        except:
            print("ext server error")
        if ret["download"] != None:
            ret["download"] = await self.get_servers(ret["download"])
        else:
            ret["can_download"] = False
        ret["ep_num"] = episode_num

        if 'countdown' in ret["player"][0]:
            ret['episode_countdown'] = True
        else:
            pass

        return ret

    async def get_servers(self, dow_link):
        if dow_link != None:
            soup = await fetch(dow_link, self.session)
            return ((i.text, i["value"]) for i in soup.find_all("option"))
        else:
            return (None, None)

    async def get_episodes_embeds_range(self, start=0, end=None):
        gen = await self.scrape_episodes()
        ed = end or self.last_episode
        if end != None:
            for i, _ in enumerate(gen):
                if i != self.last_episode - ed - 1:
                    pass
                else:
                    break
        else:
            pass
        flag = ed - start + 1
        n = 0
        for i in gen:
            if n < flag:
                n += 1
                yield self.get_embeds(i)

    async def get_download(self, download_links: tuple, episode_number: int) -> tuple:
        """ returns tuple like (link, file_name)"""
        with open("config.json") as file:
            priority = json.loads(file.read())
        available = []
        # print(type(priority))
        for i in download_links:
            # print(i[0])
            if i[0] in priority.keys():
                available.append(i)
        # print(available)
        await asyncio.sleep(0)
        flag = 999
        final = None
        for i in available:
            if list(priority.keys()).index(i[0]) < flag:
                flag = list(priority.keys()).index(i[0])
                final = i
        print(final[0])
        a = scraper(self.base_url)
        a.quality = priority[final[0]]
        a.get_final_links(final[1])
        file_name = f"{self.name} ep_{episode_number:02d}.mp4"
        # print(file_name)
        return (a.final_dow_urls[0].replace(" ", "%20"), file_name)

    async def get_from_player(self, player_links: list, episode_number: int) -> str:
        a = player(self.session)
        print(f'writing episode {episode_number}\n')
        flag = False
        if len(player_links) > 1:
            print(f'number of player links is {len(player_links)}')
            flag = True
        else:
            pass

        with open('episodes.txt', 'a+') as f:
            f.write(f'{self.name} episode {episode_number}\n')
            for i,j in await a.get_player_embeds(player_links[0]):
                # await a.get_from_server(j)
                f.write(f"\t{i}: {j}\n")
                if flag == True:
                    for i in player_links[1:]:
                        f.write(f'\t{i}\n')
                else:
                    pass
        return f'done episode {episode_number}'


class player():
    def __init__(self, session):
        self.session = session

    @staticmethod
    async def _get_from_script(script):
        a = re.findall(r"\{.+\}", str(script))[0]
        return json.loads(f"[{a}]")

    async def get_player_embeds(self, player_link: str) -> Tuple['name', 'link'] :
        soup = await fetch(player_link, self.session)
        for i in soup.find_all("script"):
            if "var" in str(i):
                result = await player._get_from_script(i)
                break
        return ((i["name"], i["src"]) for i in result)

    async def get_from_server(self, server_link):
        soup = await fetch(server_link, self.session)
        for i in soup.find_all('script'):
            x = str(i)
            if "document.write" in x and len(x) > 783:
                link = b64decode(re.search(r'\.decode\("(.+)"\)', str(i)).group(1))
                break
        return link

if __name__ == "__main__":

    # import uvloop
    # asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    async def main():
        link = "https://www2.kickassanime.rs/anime/one-piece-779470/episode-957-443972"
        async with ClientSession() as sess:
            var = kickass(sess, link)
            print(var.name)
            tasks = []
            async for i in var.get_episodes_embeds_range(700, 702):
                tasks.append(i)
            embed_result = await asyncio.gather(*tasks)

            download_tasks = []
            player_tasks = []
            for i in embed_result:
                print(f"Starting episode {i['ep_num']}")
                print(f"available ext servers are {i['ext_servers']}")
                if i["episode_countdown"] == True:
                    print(f'episode {i["ep_num"]} is still in countdown')
                    continue
                elif i["can_download"]:
                    download_tasks.append(var.get_download(i["download"], i["ep_num"]))
                else:
                    player_tasks.append(var.get_from_player(i["player"], i['ep_num']))

            links_and_names = await asyncio.gather(*download_tasks)

            def dow_maker(url, name):
                return downloader.DownloadJob(sess, url, name, os.getcwd())

            if input("\ndownload now y/n?: ") == "y":
                if len(links_and_names) != 0:
                    print("starting all downloads \nPlease Wait.....")
                    jobs = [dow_maker(*i) for i in links_and_names]
                    tasks_3 = [asyncio.ensure_future(job.download()) for job in jobs]
                    await utils.multi_progress_bar(jobs)
                    await asyncio.gather(*tasks_3)
                else:
                    print('Nothing to download')
    
            else:
                print(links_and_names)

            to_play = await asyncio.gather(*player_tasks)
            for i in to_play:
                print(i)

    asyncio.get_event_loop().run_until_complete(main())
    print("\nOMEDETO !!")
