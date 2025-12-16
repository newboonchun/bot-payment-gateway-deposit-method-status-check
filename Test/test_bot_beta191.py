import asyncio
import pytest
from playwright.async_api import async_playwright, Page, Dialog, TimeoutError
import logging
import os
import glob
import pytz
from datetime import datetime, timezone, timedelta
from telegram import Bot
import re
from telegram.error import TimedOut
from dotenv import load_dotenv

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
    log_path = os.path.join(log_dir, "BETA191_Debug.log")
    if os.path.exists(log_path):
        try: os.remove(log_path)
        except: pass

    logger = logging.getLogger('BETA191Bot')
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
    logger.info("BETA191 PAYMENT GATEWAY TEST STARTING...")
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

async def reenter_deposit_page(page):
    # Class DOM for back arrow locator
    # <div class="relative flex items-center justify-between deposit_money_div">
    #     <button type="button" class="dep_back_btn">
    #         <i class="icon-angle-back">
    
    try:
        await page.locator('button.dep_back_btn').click()
    except Exception as e:
        raise Exception("REENTER DEPOSIT PAGE - BACK BUTTON FAILED TO CLICK")
    await asyncio.sleep(3)

async def perform_login(page):
    WEBSITE_URL = "https://www.beta191.co/en-th/"
    for _ in range(3):
        try:
            log.info(f"LOGIN PROCESS - OPENING WEBSITE: {WEBSITE_URL}")
            await page.goto("https://www.beta191.co/en-th/", timeout=30000, wait_until="domcontentloaded")
            await wait_for_network_stable(page, timeout=30000)
            log.info("LOGIN PROCESS - PAGE LOADED SUCCESSFULLY")
            break
        except:
            log.warning("LOGIN PROCESS - PAGE LOADED FAILED, RETRYING")
            await asyncio.sleep(2)
    else:
        raise Exception("LOGIN PROCESS - RETRY 3 TIMES....PAGE LOADED FAILED")
        
    # Login flow beta191
    try:
        await page.get_by_role("button", name="ใช่").click()
        log.info("LOGIN PROCESS - CLOSE SLIDEDOWN BUTTON ARE CLICKED")
    except:
        log.info("LOGIN PROCESS - NO SLIDEDOWN")
    try:
        await page.get_by_role("button", name=" Login").click()
        log.info("LOGIN PROCESS - LOGIN BUTTON ARE CLICKED")
    except:
        raise Exception("LOGIN PROCESS - LOGIN BUTTON ARE FAILED TO CLICKED")
    try:
        await page.get_by_role("textbox", name="Mobile Number").click()
        await page.get_by_role("textbox", name="Mobile Number").fill("074-567-4567")
        log.info("LOGIN PROCESS - USERNAME DONE KEYED")
    except:
        raise Exception("LOGIN PROCESS - USERNAME FAILED TO KEY IN")
    try:
        await page.get_by_role("textbox", name="Enter Your Password").click()
        await page.get_by_role("textbox", name="Enter Your Password").fill("123456")
        await page.get_by_role("button", name="Login", exact=True).click()
        await asyncio.sleep(5)
        try:
            await page.get_by_role("button", name="Login", exact=True).click(timeout=5000)
            log.info("LOGIN PROCESS - USERNAME AND PASSWORD BOX KEEP LOADING, CLICK LOGIN BUTTON AGAIN")
        except:
            log.info("LOGIN PROCESS - USERNAME AND PASSWORD BOX ARE CLOSED")
        log.info("LOGIN PROCESS - PASSWORD DONE KEYED")
    except:
        raise Exception("LOGIN PROCESS - PASSWORD FAILED TO FILL IN AND LOGIN SUCCESS")
    try:
        await page.get_by_role("button", name="Skip For Later").click(timeout=10000)
        log.info("LOGIN PROCESS - ADVERTISEMENT CLOSE BUTTON ARE CLICKED")
    except:
        log.info("LOGIN PROCESS - ADVERTISEMENT CLOSE BUTTON ARE NOT CLICKED")
    try:
        await page.get_by_role("button", name="Deposit").click()
        log.info("LOGIN PROCESS - DEPOSIT BUTTON ARE CLICKED")
    except:
        raise Exception("LOGIN PROCESS - DEPOSIT BUTTON ARE FAILED TO CLICK")

async def qr_code_check(page):
    ## DETECT QR CODE BASED ON HTML CONTENT !!! ##
    try:
        #await page.wait_for_selector("iframe", timeout=3000)
        iframe_count = await page.locator("iframe").count()
        if iframe_count == 1:
            await page.wait_for_selector("iframe", timeout=3000)
        else:
            pass
        log.info("IFRAME/POP UP APPEARED. IFRAME COUNT:%s"%iframe_count)
    except Exception as e:
        iframe_count = 0
        log.info("No IFRAME/POP UP APPEARED:%s"%e)
    
    qr_selector = [
        "div.qr-image",
        "div.qr-image.position-relative",
        "div.payFrame", #for fpay-crypto
        "div[id*='qr' i]",
        "div#qrcode-container",
        "div#dowloadQr"
    ]

    qr_code_count = 0
    inner_iframe_qr = False
    
    if iframe_count != 0:
        for i in range(iframe_count):
            if qr_code_count != 0:
                break
            if inner_iframe_qr == True:
                break
            try:
                base = page.frame_locator("iframe").nth(i)
                inner_frame_count = await base.locator("iframe").count()
                log.info("QR_CODE CHECK: INNER_FRAME_COUNT:%s"%(inner_frame_count))
                for selector in qr_selector:
                    try:
                        qr_code = base.locator(selector)
                        qr_code_count = await qr_code.count()
                        log.info("QR_CODE:%s QR_CODE_COUNT:%s"%(qr_code,qr_code_count))
                        if qr_code_count != 0:
                            break
                    except Exception as e:
                        qr_code_count = 0
                        log.info("QR_CODE_CHECK LOOP SELECTOR:%s"%e)
                # proceed to inner iframe qr code check
                if qr_code_count == 0:
                    for j in range(inner_frame_count):
                        log.info("PROCEED TO INNER IFRAME CHECK....")
                        try:
                            inner_base = base.frame_locator("iframe").nth(j)
                            for selector in qr_selector:
                                try:
                                    qr_code = inner_base.locator(selector)
                                    qr_code_count = await qr_code.count()
                                    log.info("QR_CODE:%s INNER_FRAME_QR_CODE_COUNT:%s"%(qr_code,qr_code_count))
                                    if qr_code_count != 0:
                                        inner_iframe_qr = True
                                        break
                                except Exception as e:
                                    qr_code_count = 0 
                                    log.info("QR_CODE_CHECK LOOP SELECTOR:%s"%e)
                        except Exception as e:
                            log.info("INNER QR IFRAME SELECTOR ERROR:%s"%e)
            except Exception as e:
                log.info("QR_CODE_CHECK ERROR:%s"%e)
                pass

    # second stage check
    if qr_code_count == 0:
        base = page
        for selector in qr_selector:
            try:
                qr_code = base.locator(selector)
                qr_code_count = await qr_code.count()
                log.info("QR_CODE:%s , QR_CODE_COUNT:%s"%(qr_code,qr_code_count))
                if qr_code_count != 0:
                    break
            except Exception as e:
                qr_code_count = 0 
                log.info("QR_CODE_CHECK LOOP SELECTOR:%s"%e)
    
    if qr_code_count != 0:
        log.info("QR DETECTED")
    else:
        log.info("NO QR DETECTED")
    return qr_code_count

async def check_toast(page,deposit_method_button,deposit_method_text,deposit_channel):
    toast_exist = False
    # deposit method click in from the scrollbar
    try:
        await deposit_method_button.click()
        log.info("CHECK TOAST - DEPOSIT METHOD [%s] BUTTON ARE CLICKED"%deposit_method_text)
    except Exception as e:
        raise Exception("CHECK TOAST - DEPOSIT METHOD [%s] BUTTON ARE FAILED CLICKED"%deposit_method_text)
    # fill in money input amount
    try:
        input_deposit_amount_box = page.locator('input.deposit-amount-input')
        placeholder = await input_deposit_amount_box.get_attribute("placeholder")
        match = re.search(r'THB\s+(\d+)', placeholder)
        min_amount = match.group(1) if match else None
        log.info("CHECK TOAST: MINIMUM INPUT AMOUNT TO TEST: [%s]"%min_amount)
        await input_deposit_amount_box.click()
        await input_deposit_amount_box.fill("%s"%min_amount)
    except Exception as e:
        raise Exception("CHECK TOAST - MIN AMOUNT [%s] ARE NOT KEYED IN, ERROR:%s"%(min_amount,e))
    # submit button
    # class DOM: <button type="button" class="deposit_ok_btn rounded-full text-sm md:text-base font-medium px-5 py-3 w-full md:w-[70%]">ยืนยัน</button>
    try:
        submit_button = page.locator("button.deposit_ok_btn")
        await submit_button.click()
    except Exception as e:
        raise Exception("CHECK TOAST - เติมเงิน/DEPOSIT TOP UP BUTTON ARE FAILED TO CLICK, ERROR:%s"%e)

    try:
        for _ in range(20):
            toast = page.locator('div.toast-message.text-sm')
            await toast.wait_for(state="visible", timeout=5000)
            text = (await toast.inner_text()).strip()
            if await toast.count() > 0:
                toast_exist = True
                await page.screenshot(path="BETA191_%s_%s_Payment_Page.png"%(deposit_method_text,deposit_channel),timeout=30000)
                log.info("DEPOSIT METHOD:%s, DEPOSIT CHANNEL:%s GOT PROBLEM. DETAILS:[%s]"%(deposit_method_text,deposit_channel,text))
                break
            await asyncio.sleep(0.1)
    except:
            toast_exist = False
            log.info("No Toast message, no proceed to payment page, no qr code, please check what reason manually.")
    return toast_exist,text

async def perform_payment_gateway_test(page):
    exclude_list = ["Bank", "Government Savings Bank", "Government Saving Bank", "ธนาคารออมสิน", "ธนาคารกสิกรไทย", "ธนาคารไทยพาณิชย์","ธนาคาร","กสิกรไทย"]
    telegram_message = {}
    failed_reason = {}

    # locate scrollbar
    # class DOM: <div class="grid grid-cols-1 gap-4 overflow-y-auto light-scrollbar pb-[2rem] px-7">
    try:
        await asyncio.sleep(10)
        deposit_method_container = page.locator('div.grid.overflow-y-auto.light-scrollbar')
        await deposit_method_container.wait_for(state="attached")
        # locate every deposit method button in the scrollbar menu
        # class DOM for deposit_method_button: <div class="deposit-channel px-5 py-4 rounded-2xl relative">
        deposit_method_button = deposit_method_container.locator('div.deposit-channel.relative')
        deposit_method_total_count = await deposit_method_button.count()
        log.info("PERFORM PAYMENT GATEWAY TEST - DEPOSIT METHOD COUNT [%s]"%deposit_method_total_count)
        if deposit_method_total_count == 0:
            raise Exception ("PERFORM PAYMENT GATEWAY TEST - DEPOSIT METHOD COUNT = 0, SCROLLBAR DIDN'T LOCATE PROBABLY")
        for i in range(deposit_method_total_count):
            # class DOM for deposit method text
            # <div class="deposit-channel p-[0.75rem] rounded-[5px] relative overflow-hidden">
            #    <div class="flex justify-between w-full">
            #        <div class="flex items-center">
            #           <div class="w-28 h-14 flex justify-center rounded-[5px] me-6 relative">
            #                <img src="https://d2a18plfx719u2.cloudfront.net/frontend/bank_image2/promptpay.png?v=1760607913821">

            # class DOM for deposit channel text
            # <div class="deposit-channel p-[0.75rem] rounded-[5px] relative overflow-hidden">
            #     <div class="flex justify-between w-full">
            #         <div class="flex items-center">
            #              <div class="w-28 h-14 flex justify-center rounded-[5px] me-6 relative">
            #                 <img src="https://d2a18plfx719u2.cloudfront.net/frontend/bank_image2/promptpay.png?v=1760607913821">
            #                   </div><div><span class="text-sm capitalize font-medium deposit-text-title">CYPAY</span>
            btn = deposit_method_button.nth(i)
            deposit_method_image = btn.locator("img")
            deposit_method_image_link = await deposit_method_image.get_attribute("src")
            deposit_method = deposit_method_image_link.split("/")[-1].split(".")[0]
            deposit_channel = await btn.locator('span.text-sm.capitalize.font-medium.deposit-text-title').inner_text()
    
            log.info("PERFORM PAYMENT GATEWAY TEST - DEPOSIT METHOD [%s]"%deposit_method)
            #if deposit_method != 'USDT-TRC20': #FOR DEBUG
            #   continue
            # manual bank check

            # for situation deposit method = fpay_crypto (need to fan out to all sites)
            if "_" in deposit_method:
                deposit_method = deposit_method.replace("_", "-")
                log.info("PERFORM PAYMENT GATEWAY TEST - DEPOSIT METHOD AFTER _ REPLACED WITH - [%s]"%deposit_method)

            if any(manual_bank in deposit_method for manual_bank in exclude_list):
                log.info(f"DEPOSIT METHOD [{deposit_method}] IS NOT PAYMENT GATEWAY, SKIPPING CHECK...")
                continue
            else:
                pass
            # deposit method click
            try:
                btn = await deposit_method_button.nth(i).click()
                log.info("PERFORM PAYMENT GATEWAY TEST - DEPOSIT METHOD [%s] BUTTON ARE CLICKED"%deposit_method)
                # input minimum deposit amount
                # <input type="number" class="o-input !py-3 !text-sm md:!text-base o-number o-number-spinner deposit-amount-input-staging deposit-number-custom max-w-[80%] not-ios" step="1" inputmode="numeric" placeholder="0"
                # <div class="flex justify-end mt-2 font-light text-[8px] text-[#888693]">100.00 - 200,000.00 THB</div>
                
                try:
                    #if deposit_channel != 'QPAY': #FOR DEBUG
                    #    continue
                    log.info("FOUND [%s] DEPOSIT CHANNEL FOR DEPOSIT METHOD [%s]"%(deposit_channel,deposit_method))
                    input_deposit_amount_box = page.locator('input.o-input.deposit-amount-input-staging')
                    input_deposit_amount_range = await page.locator('div.flex.justify-end.font-light').inner_text()
                    match = re.search(r"[\d,.]+", input_deposit_amount_range)
                    min_amount = match.group() if match else None
                    log.info("MINIMUM INPUT AMOUNT TO TEST: [%s]"%min_amount)
                    await input_deposit_amount_box.click()
                    await input_deposit_amount_box.fill("%s"%min_amount)
                    # submit button
                    # class DOM: <button type="button" class="deposit_ok_btn rounded-full text-sm md:text-base font-medium px-5 py-3 w-full md:w-[70%]">ยืนยัน</button>
                    try:
                        submit_button = page.locator("button.deposit_ok_btn")
                        await submit_button.click()
                        await asyncio.sleep(30)
                        # QR code check
                        try:
                            qr_code_count = await qr_code_check(page)
                        except Exception as e:
                            log.info("QR CODE CHECK ERROR: [%s]"%e)
                        if qr_code_count != 0:
                            await page.screenshot(path="BETA191_%s_%s_Payment_Page.png"%(deposit_method,deposit_channel),timeout=30000)
                            telegram_message[f"{deposit_channel}_{deposit_method}"] = [f"deposit success_{date_time("Asia/Bangkok")}"]
                            failed_reason[f"{deposit_channel}_{deposit_method}"] = [f"-"]
                            await reenter_deposit_page(page)
                            continue
                        else:
                            # toast check (no real case yet, need to verify)
                            # screenshot first in case there are no toast (unidentified reason)
                            await page.screenshot(path="BETA191_%s_%s_Payment_Page.png"%(deposit_method,deposit_channel),timeout=30000)
                            await reenter_deposit_page(page)
                            try:
                                toast_exist,toast_failed_text = await check_toast(page,deposit_method_button.nth(i),deposit_method,deposit_channel)
                            except Exception as e:
                                log.info("TOAST CHECK ERROR: [%s]"%e)
                            if toast_exist:
                                telegram_message[f"{deposit_channel}_{deposit_method}"] = [f"deposit failed_{date_time("Asia/Bangkok")}"]
                                failed_reason[f"{deposit_channel}_{deposit_method}"] = [toast_failed_text]
                                log.info("TOAST DETECTED")
                                await reenter_deposit_page(page)
                                continue
                            else:
                                telegram_message[f"{deposit_channel}_{deposit_method}"] = [f"no reason found, check manually_{date_time("Asia/Bangkok")}"]
                                failed_reason[f"{deposit_channel}_{deposit_method}"] = [f"unknown reason"]
                                log.warning("UNIDENTIFIED REASON")
                                await reenter_deposit_page(page)   
                    except:
                        raise Exception ("SUBMIT BUTTON FAILED TO CLICK")  
                except Exception as e:
                    log.info("DEPOSIT CHANNEL/MINIMUM INPUT AMPONT NOT FOUND:%s"%(e))
            except Exception as e:
                raise Exception("PERFORM PAYMENT GATEWAY TEST - DEPOSIT METHOD [%s] BUTTON ARE FAILED CLICKED:%s"%(deposit_method,e))
            await asyncio.sleep(5)
    except Exception as e:
        log.info("PERFORM PAYMENT GATEWAY TEST - DEPOSIT METHOD SCROLLER/CONATINER CANNOT LOCATE:%s"%e)
    return telegram_message,failed_reason

async def telegram_send_operation(telegram_message,failed_reason,program_complete):
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
    log.info("TELEGRAM MESSAGE: [%s]"%(telegram_message))
    log.info("FAILED REASON: [%s]"%(failed_reason))
    TOKEN = os.getenv("TOKEN")
    chat_id = os.getenv("CHAT_ID")
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
            
            for key, value in failed_reason.items():
                # Split key parts
                failed_deposit_channel_method = key.split("_")
                failed_deposit_channel = failed_deposit_channel_method[0]
                failed_deposit_method  = failed_deposit_channel_method[1]

                if failed_deposit_channel == deposit_channel and failed_deposit_method == deposit_method:
                    failed_reason_text = value[0]
                    break

            log.info("METHOD: [%s], CHANNEL: [%s], STATUS: [%s], TIMESTAMP: [%s]"%(deposit_method,deposit_channel,status,timestamp))
            fail_line = f"│ **Failed Reason:** `{escape_md(failed_reason_text)}`\n" if failed_reason_text else ""
            caption = f"""*Subject: Bot Testing Deposit Gateway*  
            URL: [beta191\\.co](https://www\\.beta191\\.co/en\\-th)
            TEAM : B1T
            ┌─ **Deposit Testing Result** ──────────┐
            │ {status_emoji} **{status}** 
            │  
            │ **PaymentGateway:** `{escape_md(deposit_method) if deposit_method else "None"}`  
            │ **Channel:** `{escape_md(deposit_channel) if deposit_channel else "None"}`  
            └───────────────────────────┘

            **Failed reason**  
            {fail_line}

            **Time Detail**  
            ├─ **TimeOccurred:** `{timestamp}` """ 
            files = glob.glob("*BETA191_%s_%s*.png"%(deposit_method,deposit_channel))
            log.info("File [%s]"%(files))
            file_path = files[0]
            # Only send screenshot which status is failed
            if status != 'deposit success':
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
                pass
    else:   
        fail_msg = (
                "⚠️ *BETA191 RETRY 3 TIMES FAILED*\n"
                "OVERALL FLOW CAN'T COMPLETE DUE TO NETWORK ISSUE OR INTERFACE CHANGES IN LOGIN PAGE OR CLOUDFLARE BLOCK\n"
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

async def telegram_send_summary(telegram_message,date_time):
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
    log.info("TELEGRAM MESSAGE: [%s]"%(telegram_message))
    TOKEN = os.getenv("TOKEN")
    chat_id = os.getenv("CHAT_ID")
    bot = Bot(token=TOKEN)
    log.info("TELEGRAM_MESSAGE:%s"%telegram_message)
    succeed_records = []
    failed_records  = []
    unknown_records = []
    for key, value_list in telegram_message.items():
            # Split key parts
            deposit_channel_method = key.split("_")
            deposit_channel = deposit_channel_method[0]
            deposit_method  = deposit_channel_method[1]
            method = escape_md(deposit_method)
            channel = escape_md(deposit_channel)
            # The value list contains one string like: "deposit success - 2025-11-26 14:45:24"
            value = value_list[0]
            status, timestamp = value.split("_")
            if status == 'deposit success':
                succeed_records.append((method, channel))           
            elif status == 'deposit failed':
                failed_records.append((method, channel))
            else:
                unknown_records.append((method, channel))
            succeed_block = ""
            if succeed_records:
                items = [f"│ **• Method:{m}**  \n│   ├─ Channel:{c}  \n│" for m, c in succeed_records]
                succeed_block = f"┌─ ✅ Success **Result** ────────────┐\n" + "\n".join(items) + "\n└───────────────────────────┘"
        
            failed_block = ""
            if failed_records:
                items = [f"│ **• Method:{m}**  \n│   ├─ Channel:{c}  \n│" for m, c in failed_records]
                failed_block = f"\n┌─ ❌ Failed **Result** ─────────────┐\n" + "\n".join(items) + "\n└───────────────────────────┘"
            
            unknown_block = ""
            if unknown_records:
                items = [f"│ **• Method:{m}**  \n│   ├─ Channel:{c}  \n│" for m, c in unknown_records]
                unknown_block = f"\n┌─ ❓ Unknown **Result** ─────────────┐\n" + "\n".join(items) + "\n└───────────────────────────┘"
            
            summary_body = succeed_block + (failed_block if failed_block else "") + (unknown_block if unknown_block else "")
            caption = f"""*Deposit Payment Gateway Testing Result Summary *  
URL: [beta191\\.co](https://www\\.beta191\\.co/en\\-th)
TEAM : B1T
TIME: {escape_md(date_time)}

{summary_body}"""

    for attempt in range(3):
        try:
            await bot.send_message(chat_id=chat_id, text=caption, parse_mode='MarkdownV2', disable_web_page_preview=True)
            log.info("SUMMARY SENT")
            break
        except TimedOut:
            log.warning(f"TELEGRAM TIMEOUT，RETRY {attempt + 1}/3...")
            await asyncio.sleep(3)
        except Exception as e:
            log.error(f"SUMMARY FAILED TO SENT: {e}")

async def clear_screenshot():
    picture_to_sent = glob.glob("*BETA191*.png")
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
                telegram_message, failed_reason = await perform_payment_gateway_test(page)
                await telegram_send_operation(telegram_message,failed_reason,program_complete=True)
                await telegram_send_summary(telegram_message,date_time('Asia/Bangkok'))
                await clear_screenshot()
                break
            except Exception as e:
                await context.close()
                await browser.close()
                log.warning("RETRY ROUND [%s] ERROR: [%s]"%(attempt,e))
                log.info("NETWORK ISSUE, STOP HALFWAY, RETRY FROM BEGINNING...")
            
            if attempt == MAX_RETRY:
                telegram_message = {}
                failed_reason = {}
                log.warning("REACHED MAX RETRY, STOP SCRIPT")
                await telegram_send_operation(telegram_message,failed_reason,program_complete=False)
                raise Exception("RETRY 3 TIMES....OVERALL FLOW CAN'T COMPLETE DUE TO NETWORK ISSUE")