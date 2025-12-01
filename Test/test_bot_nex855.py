import asyncio
import pytest
from playwright.async_api import async_playwright, Page, Dialog, TimeoutError
import logging
import os
import glob
import requests
import time
import pytz
from datetime import datetime, timezone, timedelta
from telegram import Bot
import re
from telegram.error import TimedOut

def escape_md(text):
    if text is None: return ""
    return (str(text)
            .replace('\\', '\\\\').replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
            .replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`')
            .replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-')
            .replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}')
            .replace('.', '\\.').replace('!', '\\!'))

def date_time(country):
    current_date_time = pytz.timezone(country)
    time = datetime.now(current_date_time)
    #print("Current time in %s:"%country, time.strftime('%Y-%m-%d %H:%M:%S'))
    return time.strftime('%Y-%m-%d %H:%M:%S')

def init_logger(round_start_time):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    log_dir = os.path.join(base_dir, "Debug_Log")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "NEX855_Debug.log")
    if os.path.exists(log_path):
        try: os.remove(log_path)
        except: pass

    logger = logging.getLogger('NEX855Bot')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%H:%M:%S')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(file_formatter)
    logger.addHandler(console_handler)

    logger.info("=" * 60)
    logger.info("NEX855 PAYMENT GATEWAY TEST STARTING...")
    logger.info(f"STARTING TIME: {round_start_time.strftime('%d-%m-%Y %H:%M:%S')} GMT+7")
    logger.info("=" * 60)
    return logger

log = None

async def wait_for_network_stable(page: Page, min_stable_ms: int = 1500, timeout: int = 15000):
    start = asyncio.get_event_loop().time() * 1000
    last_request = start
    request_count = 0

    def on_request(_):
        nonlocal last_request, request_count
        request_count += 1
        last_request = asyncio.get_event_loop().time() * 1000

    page.on("request", on_request)
    page.on("requestfinished", on_request)
    page.on("requestfailed", on_request)

    try:
        while (asyncio.get_event_loop().time() * 1000 - start) < timeout:
            if request_count == 0 or (asyncio.get_event_loop().time() * 1000 - last_request) >= min_stable_ms:
                await asyncio.sleep(0.3)
                return True
            await asyncio.sleep(0.2)
        return False
    finally:
        page.remove_listener("request", on_request)
        page.remove_listener("requestfinished", on_request)
        page.remove_listener("requestfailed", on_request)

async def reenter_deposit_page(page,old_url,deposit_method,deposit_channel,min_amount,recheck):
    try:
        await page.goto("%s"%old_url)
        await asyncio.sleep(5)
        await wait_for_network_stable(page, timeout=30000)
        log.info("REENTER DEPOSIT PAGE - PAGE LOADED SUCCESSFULLY")
    except:
        raise Exception("REENTER DEPOSIT PAGE - PAGE LOADED FAILED")
    try:
        await page.get_by_role("button", name="%s"%deposit_method).click()
        log.info("REENTER DEPOSIT PAGE - DEPOSIT METHOD [%s] BUTTON ARE CLICKED"%deposit_method)
    except:
        raise Exception("REENTER DEPOSIT PAGE - DEPOSIT METHOD [%s] BUTTON ARE FAILED CLICKED"%deposit_method)
    try:
        await page.get_by_role("button", name="%s"%deposit_channel).click()
        log.info("REENTER DEPOSIT PAGE - DEPOSIT CHANNEL [%s] BUTTON ARE CLICKED"%deposit_channel)
    except:
        raise Exception("REENTER DEPOSIT PAGE - DEPOSIT CHANNEL [%s] BUTTON ARE FAILED CLICKED"%deposit_channel)
    try:
        await page.get_by_placeholder("0").click()
        await page.get_by_placeholder("0").fill("%s"%min_amount)
        log.info("REENTER DEPOSIT PAGE - MIN AMOUNT [%s] ARE KEYED IN"%min_amount)
    except:
        raise Exception("PERFORM PAYMENT GATEWAY TEST - MIN AMOUNT [%s] ARE NOT KEYED IN"%min_amount)
    if recheck:
        try:
            await page.get_by_role("button", name="Deposit").nth(1).click()
            log.info("REENTER DEPOSIT PAGE - เติมเงิน/DEPOSIT TOP UP BUTTON ARE CLICKED")
        except:
            raise Exception("REENTER DEPOSIT PAGE - เติมเงิน/DEPOSIT TOP UP BUTTON ARE FAILED TO CLICK")

        #await page.get_by_role("button", name="เติมเงิน").nth(2).click()
    else:
        pass  

async def perform_login(page):
    WEBSITE_URL = "https://www.nex855v1.com/en-th"
    for _ in range(3):
        try:
            log.info(f"LOGIN PROCESS - OPENING WEBSITE: {WEBSITE_URL}")
            await page.goto("https://www.nex855v1.com/en-th", timeout=30000, wait_until="domcontentloaded")
            await wait_for_network_stable(page, timeout=30000)
            log.info("LOGIN PROCESS - PAGE LOADED SUCCESSFULLY")
            break
        except:
            log.warning("LOGIN PROCESS - PAGE LOADED FAILED, RETRYING")
            await asyncio.sleep(2)
    else:
        raise Exception("LOGIN PROCESS - RETRY 3 TIMES....PAGE LOADED FAILED")

    try:
        await page.get_by_role("button", name="ใช่").click()
        log.info("LOGIN PROCESS - NOTIFICATION OVER 18 YEARS OLD ARE CLOSED")
    except:
        log.info("NO SLIDEDOWN, SKIP")
    try:
        await page.get_by_role("button", name="Login").click()
        log.info("LOGIN PROCESS - LOGIN BUTTON ARE CLICKED")
    except:
        raise Exception("LOGIN PROCESS - LOGIN BUTTON ARE FAILED TO CLICKED")
    try:
        await page.get_by_role("textbox", name="Enter phone number").fill("0745674567")
        log.info("LOGIN PROCESS - USERNAME DONE KEYED")
    except:
        raise Exception("LOGIN PROCESS - USERNAME FAILED TO KEY IN")
    try:
        await page.get_by_role("textbox", name="Password / 6 Digits Pin").fill("123456")
        log.info("LOGIN PROCESS - PASSWORD DONE KEYED")
    except:
        raise Exception("LOGIN PROCESS - PASSWORD FAILED TO KEY IN")
    try:
        await page.get_by_role("button", name=" Login").click()
        log.info("LOGIN PROCESS - LOGIN BUTTON ARE CLICKED")
    except:
        raise Exception("LOGIN PROCESS - LOGIN BUTTON ARE FAILED TO CLICKED")
    try:
        await page.get_by_role("button", name="Close").click()
        log.info("LOGIN PROCESS - CLOSE BUTTON ARE CLICKED")
    except:
        raise Exception("LOGIN PROCESS - CLOSE BUTTON ARE FAILED TO CLICKED")
    try:
        await page.get_by_role("button", name="Deposit").click()
        log.info("LOGIN PROCESS - DEPOSIT BUTTON ARE CLICKED")
    except:
        raise Exception("LOGIN PROCESS - DEPOSIT BUTTON ARE FAILED TO CLICK")

async def url_jump_check(page,old_url,deposit_method,deposit_channel,money_button_text,telegram_message):
    try:
        async with page.expect_navigation(wait_until="load", timeout=10000):
            try:
                await page.get_by_role("button", name="Deposit").nth(1).click()
                log.info("URL JUMP CHECK - เติมเงิน/DEPOSIT TOP UP BUTTON ARE CLICKED")
            except:
                raise Exception("URL JUMP CHECK - เติมเงิน/DEPOSIT TOP UP BUTTON ARE FAILED TO CLICK")
        
        # Wait until the URL actually changes (final page)
        await page.wait_for_function(
            "url => window.location.href !== url",
            arg=old_url,
            timeout=60000
        )
        new_url = page.url
        if new_url != old_url:
            log.info("LOADING INTO NEW PAGE [%s]"%(new_url))
            new_payment_page = True
    except TimeoutError:
        # If no navigation happened, page stays the same
        new_payment_page = False
        log.info("NO NAVIGATION HAPPENED, STAYS ON SAME PAGE [%s]"%(page.url))
    
    if new_payment_page == True:
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                await asyncio.sleep(10)
                await page.wait_for_load_state("networkidle", timeout=60000) #added to ensure the payment page is loaded before screenshot is taken
                log.info("NEW PAGE [%s] LOADED SUCCESSFULLY"%(new_url))
                await page.screenshot(path="NEX855_%s_%s_Payment_Page.png"%(deposit_method,deposit_channel),timeout=30000)
                break 
            except TimeoutError:
                log.info("TIMEOUT: PAGE DID NOT REACH NETWORKIDLE WITHIN 60s")
                retry_count += 1
                if retry_count == max_retries:
                    log.info("❌ Failed: Page did not load after 3 retries.")
                    await page.screenshot(path="NEX855_%s_%s_Payment_Page.png"%(deposit_method,deposit_channel),timeout=30000)
                    url_jump = True
                    payment_page_failed_load = True
                else:
                    log.info("RETRYING...: ATTEMPT [%s] of [%s]"%(retry_count,max_retries))
                    try:
                        await reenter_deposit_page(page,old_url,deposit_method,deposit_channel,money_button_text,recheck=1)
                    except:
                        log.info("FAILED GO BACK TO OLD PAGE [%s] AND RETRY..."%(old_url))

    if new_payment_page == False:   
        await page.screenshot(path="NEX855_%s_%s_Payment_Page.png"%(deposit_method,deposit_channel),timeout=30000)
        url_jump = False
        payment_page_failed_load = False

    if new_payment_page and retry_count<3:
        url_jump = True
        payment_page_failed_load = False
    
    return url_jump, payment_page_failed_load

async def qr_code_check(page):
    ## DETECT QR CODE BASED ON HTML CONTENT !!! ##
    try:
        await page.wait_for_selector("iframe", timeout=3000)
        iframe_count = await page.locator("iframe").count()
        log.info("IFRAME/POP UP APPEARED. IFRAME COUNT:%s"%iframe_count)
    except:
        iframe_count = 0
        log.info("No IFRAME/POP UP APPEARED")

    qr_selector = [
        "div[id*='qr' i]",
        "div#qrcode-container",
        "div#dowloadQr"
    ]

    qr_code = None

    if iframe_count != 0:
        base = page.frame_locator("iframe").nth(0)
    else:
        base = page
    
    for selector in qr_selector:
        try:
            qr_code = base.locator(selector)
            await qr_code.wait_for(state="attached", timeout=10000)
            break  # Found it, exit loop
        except:
            qr_code = None 

    if qr_code != None:
        log.info("QR DETECTED")
    
    return qr_code

async def check_toast(page,deposit_method,deposit_channel):
    toast_exist = False
    try:
        await page.get_by_role("button", name="%s"%deposit_method).click()
        log.info("CHECK TOAST - DEPOSIT METHOD [%s] BUTTON ARE CLICKED"%deposit_method)
    except:
        raise Exception("CHECK TOAST - DEPOSIT METHOD [%s] BUTTON ARE FAILED CLICKED"%deposit_method)
    try:
        await page.get_by_role("button", name="%s"%deposit_channel).click()
        log.info("CHECK TOAST - DEPOSIT CHANNEL [%s] BUTTON ARE CLICKED"%deposit_channel)
    except:
        raise Exception("CHECK TOAST - DEPOSIT CHANNEL [%s] BUTTON ARE FAILED CLICKED"%deposit_channel)
    money_input_range = page.locator('div.deposit_channel_text.flex.justify-between')
    await money_input_range.wait_for(state="attached", timeout=3000)
    money_input_range_text = (await money_input_range.inner_text())
    matches = re.findall(r"฿\s*([\d,]+)", money_input_range_text)
    if matches:
        min_amount = matches[0]            
        min_amount = min_amount.replace(",", "")  # remove comma if any
        print(min_amount)
    else:
        log.warning("NO MINIMUM DEPOSIT AMOUNT INPUT")
    try:
        await page.get_by_placeholder("0").click()
        await page.get_by_placeholder("0").fill("%s"%min_amount)
        log.info("CHECK TOAST - MIN AMOUNT [%s] ARE KEYED IN"%min_amount)
    except:
        raise Exception("CHECK TOAST - MIN AMOUNT [%s] ARE NOT KEYED IN"%min_amount)
    try:
        await page.get_by_role("button", name="Deposit").nth(1).click()
        log.info("CHECK TOAST - เติมเงิน/DEPOSIT TOP UP BUTTON ARE CLICKED")
    except:
        raise Exception("CHECK TOAST - เติมเงิน/DEPOSIT TOP UP BUTTON ARE FAILED TO CLICK")
    try:
        for _ in range(20):
            toast = page.locator('div.toast-message.text-sm')
            await toast.wait_for(state="visible", timeout=5000)
            text = (await toast.inner_text()).strip()
            if await toast.count() > 0:
                toast_exist = True
                await page.screenshot(path="NEX855_%s_%s_Payment_Page.png"%(deposit_method,deposit_channel),timeout=30000)
                log.info("DEPOSIT METHOD:%s, DEPOSIT CHANNEL:%s GOT PROBLEM. DETAILS:[%s]"%(deposit_channel,deposit_method,text))
                break
            await asyncio.sleep(0.1)
    except:
            toast_exist = False
            log.info("No Toast message, no proceed to payment page, no qr code, please check what reason manually.")
    return toast_exist

async def perform_payment_gateway_test(page):
    exclude_list = ["Government Savings Bank", "ธนาคารออมสิน", "ธนาคารกสิกรไทย", "ธนาคารไทยพาณิชย์","ธนาคาร","กสิกรไทย"]
    telegram_message = {}
    deposit_method_container = page.locator(".deposit-method-container")
    await deposit_method_container.wait_for(state="attached")
    deposit_method_button = deposit_method_container.locator("button")
    deposit_method_total_count = await deposit_method_button.count()
    for i in range(deposit_method_total_count):
        old_url = page.url
        btn = deposit_method_button.nth(i)
        deposit_method = await btn.get_attribute("aria-label")
        #if deposit_method != 'เติมเงินผ่าน QR': #FOR DEBUG
        #    continue
        # deposit method click
        try:
            await page.get_by_role("button", name="%s"%deposit_method).click()
            log.info("PERFORM PAYMENT GATEWAY TEST - DEPOSIT METHOD [%s] BUTTON ARE CLICKED"%deposit_method)
        except:
            raise Exception("PERFORM PAYMENT GATEWAY TEST - DEPOSIT METHOD [%s] BUTTON ARE FAILED CLICKED"%deposit_method)
        log.info("URL AFTER DEPOSIT METHOD [%s] BUTTON CLICK: [%s]"%(deposit_method,old_url))
        deposit_channel_container = page.locator(".deposit-channel-container")
        await deposit_channel_container.first.wait_for(state="attached")
        deposit_channel_button = deposit_channel_container.locator("button")
        deposit_channel_count = await deposit_channel_button.count()
        log.info("FOUND [%s] DEPOSIT CHANNEL FOR DEPOSIT METHOD [%s]"%(deposit_channel_count,deposit_method))
        for j in range(deposit_channel_count):
            btn = deposit_channel_button.nth(j)
            deposit_channel = await btn.get_attribute("aria-label")
            #if deposit_channel != 'GLOBALPAY': #FOR DEBUG
            #    continue
            log.info("DEPOSIT CHANNEL [%s] "%(deposit_channel))
            if any(manual_bank in deposit_channel for manual_bank in exclude_list):
                log.info(f"DEPOSIT CHANNEL [{deposit_channel}] IS NOT PAYMENT GATEWAY, SKIPPING CHECK...")
                continue
            else:
                pass
            # click deposit button...start load to payment page
            try:
                await page.get_by_role("button", name="%s"%deposit_channel).click()
                log.info("PERFORM PAYMENT GATEWAY TEST - DEPOSIT CHANNEL [%s] BUTTON ARE CLICKED"%deposit_channel)
            except:
                raise Exception("PERFORM PAYMENT GATEWAY TEST - DEPOSIT CHANNEL [%s] BUTTON ARE FAILED CLICKED"%deposit_channel)
            # input the minimum deposit amount 
            money_input_range = page.locator('div.deposit_channel_text.flex.justify-between')
            await money_input_range.wait_for(state="attached", timeout=3000)
            money_input_range_text = (await money_input_range.inner_text())
            log.info("MONEY INPUT RANGE AMOUNT: [%s]"%money_input_range_text)
            matches = re.findall(r"฿\s*([\d,]+)", money_input_range_text)
            if matches:
                min_amount = matches[0]            
                min_amount = min_amount.replace(",", "")  # remove comma if any
                log.info("MINIMUM INPUT AMOUNT TO TEST: [%s]"%min_amount)
            else:
                log.warning("NO MINIMUM DEPOSIT AMOUNT INPUT")
            try:
                await page.get_by_placeholder("0").click()
                await page.get_by_placeholder("0").fill("%s"%min_amount)
                log.info("PERFORM PAYMENT GATEWAY TEST - MIN AMOUNT [%s] ARE KEYED IN"%min_amount)
            except:
                raise Exception("PERFORM PAYMENT GATEWAY TEST - MIN AMOUNT [%s] ARE NOT KEYED IN"%min_amount)
            url_jump, payment_page_failed_load = await url_jump_check(page,old_url,deposit_method,deposit_channel,min_amount,telegram_message)
            if url_jump and payment_page_failed_load == False:
                telegram_message[f"{deposit_channel}_{deposit_method}"] = [f"deposit success_{date_time("Asia/Bangkok")}"]
                log.info("SCRIPT STATUS: URL JUMP SUCCESS, PAYMENT PAGE SUCCESS LOAD")
                await reenter_deposit_page(page,old_url,deposit_method,deposit_channel,min_amount,recheck=0)
                continue
            elif url_jump and payment_page_failed_load == True:
                telegram_message[f"{deposit_channel}_{deposit_method}"] = [f"deposit failed_{date_time("Asia/Bangkok")}"]
                log.info("SCRIPT STATUS: URL JUMP SUCCESS, PAYMENT PAGE FAILED LOAD")
                await reenter_deposit_page(page,old_url,deposit_method,deposit_channel,min_amount,recheck=0)
                continue
            else:
                pass
            qr_code = await qr_code_check(page)
            if qr_code != None:
                telegram_message[f"{deposit_channel}_{deposit_method}"] = [f"deposit success_{date_time("Asia/Bangkok")}"]
                await reenter_deposit_page(page,old_url,deposit_method,deposit_channel,min_amount,recheck=0)
                continue
            else:
                pass
            toast_exist = await check_toast(page,deposit_method,deposit_channel)
            if toast_exist:
                telegram_message[f"{deposit_channel}_{deposit_method}"] = [f"deposit failed_{date_time("Asia/Bangkok")}"]
                log.info("TOAST DETECTED")
                continue
            else:
                telegram_message[f"{deposit_channel}_{deposit_method}"] = [f"no reason found, check manually_{date_time("Asia/Bangkok")}"]
                log.warning("UNIDENTIFIED REASON")

    return telegram_message


async def telegram_send_operation(telegram_message, program_complete):
    log.info("TELEGRAM MESSAGE: [%s]"%(telegram_message))
    # Debug telegram token and chat id
    TOKEN = '8450485022:AAE-EBYI0_f1UDDZpI_CLdGywhMMi8pzYyo'
    chat_id = -5015541241
    # Production telegram token and chat id
    #TOKEN = '8415292066:AAHBpdP8yw15BhpzwoqccSovb-R26vsBq8w'
    #chat_id = -4978443446
    bot = Bot(token=TOKEN)
    if program_complete == True:
        for key, value_list in telegram_message.items():
            # Split key parts
            deposit_channel_method = key.split("_")
            deposit_channel = deposit_channel_method[0]
            deposit_method  = deposit_channel_method[1]
            # The value list contains one string like: "deposit success - 2025-11-26 14:45:24"
            value = value_list[0]
            status, timestamp = value.split("_")
            if status == 'deposit success':
                status_emoji = "✅"
            elif status == 'deposit failed':
                status_emoji = "❌"
            else:
                status_emoji = "❓"
            log.info("METHOD: [%s], CHANNEL: [%s], STATUS: [%s], TIMESTAMP: [%s]"%(deposit_method,deposit_channel,status,timestamp))
            caption = f"""*Subject: Bot Testing Deposit Gateway*  
            URL: [nex855\\.com](https://www\\.nex855\\.com/en\\-th)
            ┌─ **Deposit Testing Result** ──────────┐
            │ {status_emoji} **{status}** 
            │  
            │ **PaymentGateway:** `{escape_md(deposit_method) if deposit_method else "None"}`  
            │ **Channel:** `{escape_md(deposit_channel) if deposit_channel else "None"}`  
            └──────────────────────┘
            **Time Detail**  
            ├─ **TimeOccurred:** `{timestamp}` """ 
            files = glob.glob("*NEX855_%s_%s*.png"%(deposit_method,deposit_channel))
            log.info("File [%s]"%(files))
            file_path = files[0]
            for attempt in range(3):
                try:
                    with open(file_path, 'rb') as f:
                          await bot.send_photo(
                                chat_id=chat_id,
                                photo=f,
                                caption=caption,
                                parse_mode='MarkdownV2',
                                read_timeout=30,
                                write_timeout=30,
                                connect_timeout=30
                            )
                    log.info(f"SCREENSHOT SUCCESSFULLY SENT")
                    break
                except TimedOut:
                    log.warning(f"TELEGRAM TIMEOUT，RETRY {attempt + 1}/3...")
                    await asyncio.sleep(5)
                except Exception as e:
                    log.info("ERROR TELEGRAM BOT [%s]"%(e))
                    break
    else:
        fail_msg = (
                "⚠️ *NEX855 RETRY 3 TIMES FAILED*\n"
                "OVERALL FLOW CAN'T COMPLETE DUE TO NETWORK ISSUE OR INTERFACE CHANGES IN LOGIN PAGE\n"
                "KINDLY ASK ENGINEER TO CHECK IF ISSUE PERSISTS CONTINUOUSLY IN TWO HOURS"
            )
        try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=fail_msg,
                    parse_mode="Markdown"
                )
                log.info("FAILURE MESSAGE SENT")
        except Exception as e:
                log.error(f"FAILED TO SEND FAILURE MESSAGE: {e}")

async def clear_screenshot():
    picture_to_sent = glob.glob("*NEX855*.png")
    for f in picture_to_sent:
        os.remove(f) 

@pytest.mark.asyncio
async def test_main():
    MAX_RETRY = 3
    global log
    th_tz = pytz.timezone('Asia/Bangkok')
    round_start = datetime.now(th_tz)
    log = init_logger(round_start)
    async with async_playwright() as p:
        for attempt in range(1, MAX_RETRY + 1):
            try:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context()
                page = await context.new_page()
                await perform_login(page)
                telegram_message = await perform_payment_gateway_test(page)
                await telegram_send_operation(telegram_message,program_complete=True)
                await clear_screenshot()
                break
            except Exception as e:
                await context.close()
                await browser.close()
                log.warning("RETRY ROUND [%s] ERROR: [%s]"%(attempt,e))
                log.info("NETWORK ISSUE, STOP HALFWAY, RETRY FROM BEGINNING...")
            
            if attempt == MAX_RETRY:
                telegram_message = {}
                log.warning("REACHED MAX RETRY, STOP SCRIPT")
                await telegram_send_operation(telegram_message,program_complete=False)
                raise Exception("RETRY 3 TIMES....OVERALL FLOW CAN'T COMPLETE DUE TO NETWORK ISSUE")

