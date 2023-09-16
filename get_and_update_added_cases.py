import ast
import datetime
import re
import time
import urllib.request
from typing import Optional

import requests
from bs4 import BeautifulSoup


def url_to_bs(url: str) -> BeautifulSoup:
    """URL から bs4.BeautifulSoup を取得"""
    with urllib.request.urlopen(url) as res:
        html_data = res.read().decode("utf-8")
    time.sleep(1)
    return BeautifulSoup(html_data, "html.parser")


def url_to_bs_login(password: str, url: str) -> BeautifulSoup:
    """AtCoder のログインが必要な URL から、認証して bs4.BeautifulSoup を取得"""
    url = url.replace("/", "%2F").replace(":", "%3A").replace("?", "%3F").replace("=", "%3D").replace("&", "%26")
    url = f"https://atcoder.jp/login?continue={url}"
    session = requests.session()
    response = session.get(url)
    time.sleep(1)
    bs = BeautifulSoup(response.text, "html.parser")

    authenticity = bs.find(attrs={"name": "csrf_token"}).get("value")
    cookie = response.cookies

    # ログインして内容を取得
    info = {"username": "Tomii9273", "password": password, "csrf_token": authenticity}
    response = session.post(url, data=info, cookies=cookie)
    time.sleep(1)
    return BeautifulSoup(response.text, "html.parser")


def get_contest_names_and_start_times() -> list[tuple[str, datetime.datetime]]:
    """「過去のコンテスト」のページから、14 日以内に開始された ABC, ARC, AGC の (コンテスト名, 開始時刻) の一覧を取得"""
    contest_names_and_times: list[tuple[str, datetime.datetime]] = []

    bs = url_to_bs("https://atcoder.jp/contests/archive")

    body_data = (
        bs.find("div", {"class": "table-responsive"})
        .find("table", {"class": "table table-default table-striped table-hover table-condensed table-bordered small"})
        .find("tbody")
    )
    contest_blocks = body_data.find_all("tr")
    for block in contest_blocks:
        contest_name = block.find_all("td")[1].find("a", href=True)["href"].split("/")[-1]
        start_time = block.find("time").text
        start_time = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S+0900")
        now_time = datetime.datetime.now()
        if start_time >= now_time - datetime.timedelta(days=14) and re.fullmatch("a[brg]c[0-9]{3}", contest_name):
            contest_names_and_times.append((contest_name, start_time))

    return contest_names_and_times


def get_task_names(contest_name: str) -> list[str]:
    """コンテスト名から問題名の一覧を取得"""
    task_names = []

    bs = url_to_bs(f"https://atcoder.jp/contests/{contest_name}/tasks")

    body_data = (
        bs.find("div", {"class": "panel panel-default table-responsive"})
        .find("table", {"class": "table table-bordered table-striped"})
        .find("tbody")
    )
    task_blocks = body_data.find_all("tr")
    for block in task_blocks:
        task_name = block.find_all("td")[1].find("a", href=True)["href"].split("/")[-1]
        task_names.append(task_name)

    return task_names


def get_testcase_names(
    password: str, contest_name: str, task_name: str, start_time: Optional[datetime.datetime]
) -> list[str]:
    """
    コンテスト名と問題名からテストケースを取得
    start_time が指定されたなら start_time 以降の最初の提出、そうでないなら最新の提出を見る
    """

    if start_time is None:
        url = (
            f"https://atcoder.jp/contests/{contest_name}/submissions"
            f"?desc=true&f.LanguageName=&f.Status=&f.Task={task_name}&f.User=&orderBy=created&page=1"
        )  # 提出日時の降順
    else:
        url = (
            f"https://atcoder.jp/contests/{contest_name}/submissions"
            f"?f.LanguageName=&f.Status=&f.Task={task_name}&f.User=&orderBy=created&page=1"
        )  # 提出日時の昇順

    bs = url_to_bs_login(password, url)

    body_data = (
        bs.find("div", {"class": "table-responsive"})
        .find("table", {"class": "table table-bordered table-striped small th-center"})
        .find("tbody")
    )
    submission_blocks = body_data.find_all("tr")
    target_id = ""
    for block in submission_blocks:
        submit_time = block.find("time").text
        submit_time = datetime.datetime.strptime(submit_time, "%Y-%m-%d %H:%M:%S+0900")
        submission_id = block.find_all("td")[-1].find("a", href=True)["href"].split("/")[-1]
        status = block.find_all("td")[6].text  # 「AC」などのジャッジ結果。ジャッジ途中だと「15/20 TLE」とかになる。
        if (start_time is None or submit_time >= start_time) and status in [
            "AC",
            "WA",
            "TLE",
            "MLE",
            "RE",
        ]:  # CE の提出はテストケースが見られないので除外。他にも見られないものがありそうなので、安全のためよく出るものだけを指定。
            target_id = submission_id
            break
    testcases: list[str] = []
    if target_id != "":
        print("target_id:", target_id)
        testcases = id_to_cases(contest_name, target_id)
    return testcases


def id_to_cases(contest_name: str, submission_id: str) -> list[str]:
    """提出 ID からテストケース一覧を取得"""
    testcases: list[str] = []

    bs = url_to_bs(f"https://atcoder.jp/contests/{contest_name}/submissions/{submission_id}")

    body_data = bs.find_all("div", {"class": "panel panel-default"})[3].find(
        "table", {"class": "table table-bordered table-striped th-center"}
    )

    body_data = body_data.find("tbody")
    testcase_blocks = body_data.find_all("tr")
    for block in testcase_blocks:
        testcase = block.find_all("td")[0].text
        testcases.append(testcase)

    return testcases


def get_and_update_added_cases(password: str) -> list[tuple[str, str, list[str]]]:
    """
    14 日以内に開始された ABC, ARC, AGC の各問題について、
    前回確認時点 (無い場合、コンテスト開始直後時点) から新たに追加されたテストケース一覧を取得し、
    testcases.txt を更新
    """
    all_added_cases = []
    with open("testcases.txt", "r") as f:
        first_line = f.readline().strip()
        exist_data = ast.literal_eval(first_line)

    contest_names_and_times = get_contest_names_and_start_times()

    print("確認するコンテストと開始時刻の一覧", contest_names_and_times)
    for contest_name, start_time in contest_names_and_times:
        print(contest_name, start_time)
        task_names = get_task_names(contest_name)
        print("task_names:", task_names)

        for task_name in task_names:
            print(task_name, "start")
            if (contest_name, task_name) in exist_data:
                testcases_before = exist_data[(contest_name, task_name)]
            else:
                testcases_before = get_testcase_names(password, contest_name, task_name, start_time)
            testcases_after = get_testcase_names(password, contest_name, task_name, None)

            testcases_only_before = set(testcases_before) - set(testcases_after)
            testcases_only_after = set(testcases_after) - set(testcases_before)

            print("testcases_only_before:", testcases_only_before)
            print("testcases_only_after:", testcases_only_after)
            assert testcases_before == set() or testcases_only_before == set()

            if testcases_only_after != set():
                added_cases = sorted(list(testcases_only_after))
                all_added_cases.append((contest_name, task_name, added_cases))

            exist_data[(contest_name, task_name)] = testcases_after

    with open("testcases.txt", "w") as f:
        print("update testcases.txt")
        f.write(str(exist_data))

    return all_added_cases


# ツイートをしない手動テスト実行
if __name__ == "__main__":
    password = input("Password?: ")
    all_added_cases = get_and_update_added_cases(password)
    print(all_added_cases)
    # testcases.txt が更新されるので、必要なら手動で元に戻す
