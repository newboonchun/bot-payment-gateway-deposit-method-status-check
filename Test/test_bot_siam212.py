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
    log_path = os.path.join(log_dir, "SIAM212_Debug.log")
    if os.path.exists(log_path):
        try: os.remove(log_path)
        except: pass

    logger = logging.getLogger('SIAM212Bot')
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
    logger.info("SIAM212 PAYMENT GATEWAY TEST STARTING...")
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
    for attempt in range(1, 3):
        try:
            log.info(f"Trying to goto URL attempt {attempt}/{3}: {old_url}")

            response = await page.goto(old_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            await wait_for_network_stable(page, timeout=30000)

            if response and response.ok:
                log.info("REENTER DEPOSIT PAGE - PAGE LOADED SUCCESSFULLY")
                break
            else:
                # if response is None or not ok
                log.warning("Navigation response not OK")
        except:
            log.info("REENTER DEPOSIT PAGE - NETWORK NOT STABLE YET, CURRENT PAGE URL:%s"%page.url)
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
            deposit_button = page.locator('.btn_deposits')
            await deposit_button.wait_for(state="visible", timeout=10000)
            await deposit_button.click()
            log.info("REENTER DEPOSIT PAGE - เติมเงิน/DEPOSIT TOP UP BUTTON ARE CLICKED")
        except:
            raise Exception("REENTER DEPOSIT PAGE - เติมเงิน/DEPOSIT TOP UP BUTTON ARE FAILED TO CLICK")
    else:
        pass  

async def perform_login(page):
    WEBSITE_URL = "https://www.siam212th11.com/en-th"
    for _ in range(3):
        try:
            log.info(f"LOGIN PROCESS - OPENING WEBSITE: {WEBSITE_URL}")
            await page.goto("https://www.siam212th11.com/en-th", timeout=30000, wait_until="domcontentloaded")
            await wait_for_network_stable(page, timeout=30000)
            log.info("LOGIN PROCESS - PAGE LOADED SUCCESSFULLY")
            break
        except:
            log.warning("LOGIN PROCESS - PAGE LOADED FAILED, RETRYING")
            await asyncio.sleep(2)
    else:
        raise Exception("LOGIN PROCESS - RETRY 3 TIMES....PAGE LOADED FAILED")
        
    # Login flow siam212
    try:
        first_advertisement_dont_show_checkbox = page.locator(".o-checkbox").first
        await first_advertisement_dont_show_checkbox.wait_for(state="visible", timeout=10000)
        await first_advertisement_dont_show_checkbox.click()
        await page.get_by_role("button", name="Close").click()
    except:
        log.info("LOGIN PROCESS - FIRST ADVERTISEMENT DIDN'T APPEARED")
    try:
        await page.locator("iframe[title=\"Contact us\"]").content_frame.locator(".Chat_icon__wrap_3840H.Chat_icon__wrap_shadow_14Bbe.view_btn_chat_pglag").click()
    except:
        log.info("LOGIN PROCESS - CHAT ICON BOX DIDN'T APPEARED")
    try:
        login_container = page.locator('div.flex.relative.items-center')
        login_buttons = login_container.locator("button.topbar_btn_1", has_text="Login")
        count = await login_buttons.count()
        for i in range(count):
            try:
                login_button = login_buttons.nth(i)
                await login_button.wait_for(state="visible", timeout=10000)
                await login_button.click()
                log.info("LOGIN PROCESS - LOGIN BUTTON (%s) ARE CLICKED"%(i+1))
            except Exception as e:
                log.info("LOGIN PROCESS - LOGIN BUTTON (%s) ARE FAILED TO CLICK"%(i+1))
    except Exception as e:
        log.info("LOGIN PROCESS - LOGIN CONTAINER FAILED TO LOCATE %s"%e)
        raise Exception("LOGIN PROCESS - LOGIN BUTTON ARE FAILED CLICKED")
    try:
        await page.get_by_role("textbox", name="09xxxxxxx").click()
        await page.get_by_role("textbox", name="09xxxxxxx").fill("0745674567")
        #<button type="submit" class="new-reg-buttons btn !font-bold !flex gap-3 justify-center items-center !py-3.5 rounded-md w-full text-sm uppercase" aria-label="Next">
        login_button = page.locator('button.new-reg-buttons')
        await login_button.click()
        log.info("LOGIN PROCESS - USERNAME DONE KEYED")
    except:
        raise Exception("LOGIN PROCESS - USERNAME FAILED TO KEY IN")
    try:
        await page.get_by_role("textbox", name="One-time password").fill("123456")
        log.info("LOGIN PROCESS - PASSWORD DONE KEYED")
    except:
        raise Exception("LOGIN PROCESS - PASSWORD FAILED TO FILL IN")
    try:
        advertisement_close_button = page.locator(".icon-close.text-lg")
        await advertisement_close_button.click()
        log.info("LOGIN PROCESS - ADVERTISEMENT CLOSE BUTTON ARE CLICKED")
    except:
        log.info("LOGIN PROCESS - ADVERTISEMENT CLOSE BUTTON ARE NOT CLICKED")
    try:
        deposit_topbar_container = page.locator('div.wallet-container-desktop')
        deposit_topbar_button = deposit_topbar_container.locator('button.topbar_btn_2:has-text("Deposit")')
        await deposit_topbar_button.click()
        log.info("LOGIN PROCESS - DEPOSIT BUTTON ARE CLICKED")
    except:
        raise Exception("LOGIN PROCESS - DEPOSIT BUTTON ARE FAILED TO CLICK")
    #await page.get_by_role("button", name="100").click()
    #await page.get_by_role("button", name="Deposit").nth(1).click()

async def url_jump_check(page,old_url,deposit_method,deposit_channel,money_button_text,telegram_message):
    try:
        async with page.expect_navigation(wait_until="load", timeout=10000):
            try:
                deposit_button = page.locator('.btn_deposits')
                await deposit_button.wait_for(state="visible", timeout=10000)
                await deposit_button.click()
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
                await page.screenshot(path="SIAM212_%s_%s_Payment_Page.png"%(deposit_method,deposit_channel),timeout=30000)
                break 
            except TimeoutError:
                log.info("TIMEOUT: PAGE DID NOT REACH NETWORKIDLE WITHIN 60s")
                retry_count += 1
                if retry_count == max_retries:
                    log.info("❌ Failed: Page did not load after 3 retries.")
                    await page.screenshot(path="SIAM212_%s_%s_Payment_Page.png"%(deposit_method,deposit_channel),timeout=30000)
                    url_jump = True
                    payment_page_failed_load = True
                else:
                    log.info("RETRYING...: ATTEMPT [%s] of [%s]"%(retry_count,max_retries))
                    try:
                        await reenter_deposit_page(page,old_url,deposit_method,deposit_channel,money_button_text,recheck=1)
                    except:
                        log.info("FAILED GO BACK TO OLD PAGE [%s] AND RETRY..."%(old_url))

    if new_payment_page == False:  
        await page.screenshot(path="SIAM212_%s_%s_Payment_Page.png"%(deposit_method,deposit_channel),timeout=30000)
        url_jump = False
        payment_page_failed_load = False

    if new_payment_page and retry_count<3:
        url_jump = True
        payment_page_failed_load = False
    
    return url_jump, payment_page_failed_load

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
        "div[id*='qr' i]",
        "div#qrcode-container",
        "div#dowloadQr"
    ]

    qr_code_count = 0

    if iframe_count != 0:
        for i in range(iframe_count):
            if qr_code_count != 0:
                break
            try:
                base = page.frame_locator("iframe").nth(i)
                for selector in qr_selector:
                    try:
                        qr_code = base.locator(selector)
                        #log.info("QR_CODE:%s"%qr_code)
                        #await qr_code.wait_for(state="attached", timeout=5000)
                        qr_code_count = await qr_code.count()
                        log.info("QR_CODE:%s QR_CODE_COUNT:%s"%(qr_code,qr_code_count))
                        if qr_code_count != 0:
                            break
                    except Exception as e:
                        log.info("QR_CODE_CHECK LOOP SELECTOR:%s"%e)
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
                log.info("QR_CODE_CHECK LOOP SELECTOR:%s"%e)

    if qr_code_count != 0:
        log.info("QR DETECTED")
    else:
        log.info("NO QR DETECTED")
    
    return qr_code_count

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
        deposit_button = page.locator('.btn_deposits')
        await deposit_button.wait_for(state="visible", timeout=10000)
        await deposit_button.click()
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
                await page.screenshot(path="SIAM212_%s_%s_Payment_Page.png"%(deposit_method,deposit_channel),timeout=30000)
                log.info("DEPOSIT METHOD:%s, DEPOSIT CHANNEL:%s GOT PROBLEM. DETAILS:[%s]"%(deposit_channel,deposit_method,text))
                break
            await asyncio.sleep(0.1)
    except:
            toast_exist = False
            log.info("No Toast message, no proceed to payment page, no qr code, please check what reason manually.")
    return toast_exist,text

async def perform_payment_gateway_test(page):
    exclude_list = ["Government Savings Bank", "Government Saving Bank", "ธนาคารออมสิน", "ธนาคารกสิกรไทย", "ธนาคารไทยพาณิชย์","ธนาคาร","กสิกรไทย"]
    telegram_message = {}
    failed_reason = {}
    await page.locator(".deposit-button-method").nth(0).wait_for(state="attached")
    try:
        deposit_method_total_count = await page.locator(".deposit-button-method").count()
        log.info("Deposit method button count:%s"%deposit_method_total_count)
    except Exception as e:
        log.info("Deposit method button:%s"%e)
    for i in range(deposit_method_total_count):
        old_url = page.url
        btn = page.locator(".deposit-button-method").nth(i)
        await page.locator(".deposit-button-method").nth(i).wait_for(state="attached")
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
            manual_bank = False
            btn = deposit_channel_button.nth(j)
            deposit_channel = await btn.get_attribute("aria-label")
            #if deposit_channel != 'FPAY-CRYPTO': #FOR DEBUG
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
            # EXTRA MANUAL BANK CHECK ##
            try:
               manual_bank_text_count = await page.locator('div.deposit_information_content_labels').count()
               for count in range(manual_bank_text_count):
                   manual_bank_text = await page.locator('div.deposit_information_content_labels').nth(count).inner_text(timeout=3000)
                   log.info("MANUAL BANK TEXT:%s"%manual_bank_text)
                   if "Bank Name" in manual_bank_text:
                       await reenter_deposit_page(page,old_url,deposit_method,deposit_channel,min_amount,recheck=0)
                       log.info("MANUAL BANK TEXT FOUND:%s"%manual_bank_text)
                       manual_bank = True
                       break
               if manual_bank == True:
                   log.info(f"DEPOSIT CHANNEL [{deposit_channel}] IS NOT PAYMENT GATEWAY, SKIPPING CHECK...")
                   continue
               else:
                   log.info("NO MANUAL BANK TEXT FOUND:%s"%e)
                   pass
            except Exception as e:
               log.info("NO MANUAL BANK TEXT FOUND:%s"%e)
               pass
            if url_jump and payment_page_failed_load == False:
                telegram_message[f"{deposit_channel}_{deposit_method}"] = [f"deposit success_{date_time("Asia/Bangkok")}"]
                failed_reason[f"{deposit_channel}_{deposit_method}"] = [f"-"]
                log.info("SCRIPT STATUS: URL JUMP SUCCESS, PAYMENT PAGE SUCCESS LOAD")
                await reenter_deposit_page(page,old_url,deposit_method,deposit_channel,min_amount,recheck=0)
                continue
            elif url_jump and payment_page_failed_load == True:
                telegram_message[f"{deposit_channel}_{deposit_method}"] = [f"deposit failed_{date_time("Asia/Bangkok")}"]
                failed_reason[f"{deposit_channel}_{deposit_method}"] = [f"payment page failed load"]
                log.info("SCRIPT STATUS: URL JUMP SUCCESS, PAYMENT PAGE FAILED LOAD")
                await reenter_deposit_page(page,old_url,deposit_method,deposit_channel,min_amount,recheck=0)
                continue
            else:
                pass
            qr_code_count = await qr_code_check(page)
            if qr_code_count != 0:
                telegram_message[f"{deposit_channel}_{deposit_method}"] = [f"deposit success_{date_time("Asia/Bangkok")}"]
                failed_reason[f"{deposit_channel}_{deposit_method}"] = [f"-"]
                await reenter_deposit_page(page,old_url,deposit_method,deposit_channel,min_amount,recheck=0)
                continue
            else:
                pass
            toast_exist, toast_failed_text = await check_toast(page,deposit_method,deposit_channel)
            if toast_exist:
                telegram_message[f"{deposit_channel}_{deposit_method}"] = [f"deposit failed_{date_time("Asia/Bangkok")}"]
                failed_reason[f"{deposit_channel}_{deposit_method}"] = [toast_failed_text]
                log.info("TOAST DETECTED")
                continue
            else:
                telegram_message[f"{deposit_channel}_{deposit_method}"] = [f"no reason found, check manually_{date_time("Asia/Bangkok")}"]
                failed_reason[f"{deposit_channel}_{deposit_method}"] = [f"unknown reason"]
                log.warning("UNIDENTIFIED REASON")

    return telegram_message, failed_reason


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
            URL: [siam212\\.com](https://www\\.siam212th11\\.com/en\\-th)
            TEAM : S2T
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
            files = glob.glob("*SIAM212_%s_%s*.png"%(deposit_method,deposit_channel))
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
                "⚠️ *SIAM212 RETRY 3 TIMES FAILED*\n"
                "OVERALL FLOW CAN'T COMPLETE DUE TO NETWORK ISSUE OR INTERFACE CHANGES IN LOGIN PAGE OR CLOUDFLARE BLOCK\n"
                "KINDLY CONTACT PAYMENT TEAM TO CHECK IF ISSUE PERSISTS CONTINUOUSLY IN TWO HOURS"
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
                unknown_block = f"\n┌─ ❓Failed **Result** ─────────────┐\n" + "\n".join(items) + "\n└───────────────────────────┘"
            
            summary_body = succeed_block + (failed_block if failed_block else "") + (unknown_block if unknown_block else "")
            caption = f"""*Deposit Payment Gateway Testing Result Summary *  
URL: [siam212\\.com](https://www\\.siam212th11\\.com/en\\-th)
TEAM : S2T
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
    picture_to_sent = glob.glob("*SIAM212*.png")
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
                telegram_message,failed_reason = await perform_payment_gateway_test(page)
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
                log.warning("REACHED MAX RETRY, STOP SCRIPT")
                await telegram_send_operation(telegram_message,failed_reason,program_complete=False)
                raise Exception("RETRY 3 TIMES....OVERALL FLOW CAN'T COMPLETE DUE TO NETWORK ISSUE")