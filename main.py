# The libraries
import cloudscraper # TBH, should have just used selenium if ik it would be this much of a pain.
from bs4 import BeautifulSoup
import re
import pandas as pd
import time
import random as rd
from tqdm.notebook import tqdm
from typing import *
import json
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from datetime import datetime

# For the GUI colours later
BG_COLOR = "#212121"
FG_COLOR = "#E0E0E0"
ACCENT_COLOR = "#BB86FC"
SEC_COLOR = "#2C2C2C"
SUCCESS_COLOR = "#03DAC6"
WARN_COLOR = "#FFB74D"
ERR_COLOR = "#CF6679"
HINT_COLOR = "#757575"


available_filters = {
    "manufacturers": ['Apple', 'Samsung', 'Google', 'OnePlus', 'Motorola', 'Sony', 'Xiaomi', 'Nokia', 'Honor', 'DOOGEE', 'Blackview', 'OSCAL', 'Nothing',
                       'Asus', 'HTC', 'Huawei', 'HMD', 'BlackBerry', 'ZTE', 'RedMagic', 'LG', 'Kyocera', 'Fairphone', 'Alcatel', 'BLU', 'Razer', 'realme', 'Essential',
                        'TCL', 'Orbic', 'CAT', 'RED', 'BOOX', 'Lenovo', 'OPPO', 'Microsoft', 'Acer', 'Garmin', 'Amazon', 'NOA', 'Meizu', 'nubia', 'GIGABYTE', 'Gionee', 'vivo', 'Panasonic',
                        'HP', 'Sony Ericsson', 'Maxwest', 'Verizon', 'Yota', 'Doro', 'T-Mobile', 'Sprint', 'Palm', 'Sanyo', 'Casio', 'VERZO', 'TAG Heuer', 'Xolo', 'VIZIO', 'Fujitsu', 'UMX',
                        'Garmin-Asus', 'Airo Wireless', 'TerreStar', 'Lumigon', 'FiGO', 'NIU', 'altek', 'Micromax', 'ARCHOS', 'Best Buy', 'Verykool', 'Notion Inc', 'Vertu', 'Sonim', 'Karbonn',
                        'ICEMOBILE', 'Emporia', 'Philips', 'Dell', 'ViewSonic', 'Toshiba', 'Barnes & Noble', 'Nvidia', 'PCD', 'Jolla', 'Eten', 'mobiado', 'i-mate', 'General Mobile', 
                        'Fusion Garage', 'INQ', 'Videocon', 'Coolpad', 'LAVA', 'Saygus', 'Yezz', 'Plum', 'Celkon', 'i-mobile', 'Spice Mobile', 'Zen Mobile', 'Velocity', 'COWON', 'Kogan',
                        'AT&T', 'VKMobile', 'Benq-Siemens', 'Helio', 'Haier', 'Lemon Mobiles', 'Handspring', 'Bird', 'Danger', 'WND', 'O2', 'Latte', 'Siemens', 'Pantech', 'Firefly Mobile',
                        'Cricket', 'Orange', 'Fly', 'Mitsubishi', 'MiTAC', 'Amoi', 'Sierra Wireless', 'Neonode', 'Sendo', 'Maxon', 'Hitachi', 'Sharp', 'NEC', 'Sagem', 'BenQ', 'Ericsson'],
                        
    "deviceType": { "Basic phone"    : "f[53][bp]=1221",
                    "Feature phone"  : "f[53][fp]=1222",
                    "Smartphone"     : "f[53][sp]=1223",
                    "Tablet"         : "f[53][t]=1612",
                    "Smartwatch"     : "f[53][sw]=2580"}
}

# For the logger
class RichLogger:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.text_widget.tag_config("INFO", foreground=FG_COLOR)
        self.text_widget.tag_config("SUCCESS", foreground=SUCCESS_COLOR)
        self.text_widget.tag_config("WARN", foreground=WARN_COLOR)
        self.text_widget.tag_config("ERROR", foreground=ERR_COLOR)
        self.text_widget.tag_config("TIME", foreground=HINT_COLOR) 

    def log(self, message, level="INFO"):
        now = datetime.now().strftime("%H:%M:%S")
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", f"[{now}] ", "TIME")
        
        if level == "INFO": self.text_widget.insert("end", "[INFO] ", "INFO")
        elif level == "SUCCESS": self.text_widget.insert("end", "[DONE] ", "SUCCESS")
        elif level == "WARN": self.text_widget.insert("end", "[WARN] ", "WARN")
        elif level == "ERROR": self.text_widget.insert("end", "[FAIL] ", "ERROR")
            
        self.text_widget.insert("end", f"{message}\n", level)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

# Edired core scraping logic
class ScraperLogic:
    def __init__(self, logger_callback, total_prog_cb, page_prog_cb, status_callback, mode_callback):
        self.log = logger_callback         
        self.update_total = total_prog_cb 
        self.update_page = page_prog_cb
        self.update_status = status_callback
        self.toggle_mode = mode_callback     
        self.driver = cloudscraper.create_scraper()
        self.gathered_data = {}
        self.should_stop = False

    def build_url(self, manufacturers, releaseYear, deviceType):
        url = "https://www.phonearena.com/phones"
        if manufacturers:
            url += "/manufacturers/"
            url += ",".join([m.lower().replace(" ", "-") for m in manufacturers])
            self.use_manufacturer_filter = True
        else:
            self.use_manufacturer_filter = False

        has_query = False
        if releaseYear:
            url += "?f[y]="
            if len(releaseYear) > 1:
                start, end = min(releaseYear), max(releaseYear)
                url += ','.join([str(i) for i in range(start, end+1)])
            else:
                url += str(releaseYear[0])
            has_query = True

        if deviceType:
            connector = "&" if has_query else "?"
            if "?" in url and not has_query: connector = "&"
            dt_params = [available_filters["deviceType"][t] for t in deviceType]
            url += connector + "&".join(dt_params)
            
        return url

    def scrape_single_phone(self, url):
        try:
            r = self.driver.get(url)
            soup = BeautifulSoup(r.content, "html5lib")
            data = {}
            try:
                widget = soup.find("div", attrs={"class": "widgetQuickSpecs"})
                rd = widget.find("div", attrs={"class":"released specs-element"}).find("span", attrs={"class":"specs-element-desc"}).text.strip()
                data["Release date"] = rd
            except:
                data["Release date"] = "N/A"

            full_spec = soup.find("section", attrs={"class": "page__section page__section_specs"})
            if full_spec:
                tables = full_spec.find_all("div", attrs={"class": "widgetSpecs"})
                for t in tables:
                    cat_name = t.find("th").text.strip()
                    cat_data = {}
                    rows = t.find_all("tr", attrs={"class":"specs-table-title"})
                    for row in rows:
                        k = row.find("th").text.strip()
                        v = row.find("td").text.strip()
                        cat_data[k] = v
                    data[cat_name] = cat_data
            return data
        except Exception as e:
            self.log(f"Failed to scrape specs: {e}", "WARN")
            return {}

    def run(self, manufacturers, years, types, min_delay, max_delay, save_path, save_csv):
        url = self.build_url(manufacturers, years, types)
        self.log(f"Target URL: {url}")
        
        self.toggle_mode("indeterminate") 
        self.update_status("Connecting to PhoneArena...")
        
        try:
            r = self.driver.get(url)
            soup = BeautifulSoup(r.content, "html5lib")
        except Exception as e:
            self.toggle_mode("determinate") # Stop bouncing
            self.log(f"Connection Error: {e}", "ERROR")
            return

        try:
            nav = soup.find("nav", attrs={"data-target":"finder-content"})
            if nav:
                max_page = int(nav.find_all("li", attrs={"class": "item"})[-2].text)
            else:
                max_page = 1
        except:
            max_page = 1

        self.log(f"Found {max_page} pages of results.", "SUCCESS")
        
        self.toggle_mode("determinate")
        self.update_total(0)
        self.update_page(0)
        
        total_phones_estimate = max_page * 20 
        phones_scraped = 0
        
        base_url_pattern = url
        if max_page > 1:
            if self.use_manufacturer_filter:
                match = re.search(r'manufacturers/[a-zA-Z0-9,-]+', url, re.IGNORECASE)
                pattern_chunk = match[0] if match else ""
            else:
                match = re.search(r'/phones', url, re.IGNORECASE)
                pattern_chunk = match[0] if match else ""
        
        for page_num in range(1, max_page + 1):
            if self.should_stop: break
            
            self.update_page(0) # Reset page bar for new page
            self.log(f"Processing Page {page_num}/{max_page}...", "INFO")
            self.update_status(f"Scanning Page {page_num}...")
            
            if page_num > 1:
                new_url = url.replace(pattern_chunk, pattern_chunk + f"/page/{page_num}")
                r = self.driver.get(new_url)
                soup = BeautifulSoup(r.content, "html5lib")
                time.sleep(rd.uniform(min_delay, max_delay))

            results_div = soup.find("div", attrs={"class": "results"})
            if not results_div:
                self.log("No results container found on this page.", "WARN")
                continue
                
            phone_tiles = results_div.find_all("div", attrs={"class": "tile-phone"})
            total_on_page = len(phone_tiles)
            
            for i, phone in enumerate(phone_tiles):
                if self.should_stop: break
                
                name = phone.find("a", attrs={"class": "tile-title"}).text.strip()
                href = phone.find("a", attrs={"class": "tile-title"}).get("href")
                
                self.update_status(f"Scraping: {name}")
                phone_data = self.scrape_single_phone(href)
                self.gathered_data[name] = phone_data
                
                phones_scraped += 1
                self.log(f"Scraped {name}", "INFO")
                
                # Update Bars
                # 1. Page Progress
                page_prog = ((i + 1) / total_on_page) * 100
                self.update_page(page_prog)
                
                # 2. Total Progress
                total_prog = min(99, (phones_scraped / total_phones_estimate) * 100)
                self.update_total(total_prog)
                
                time.sleep(rd.uniform(min_delay, max_delay))

        self.update_total(100)
        self.update_page(100)
        self.update_status("Saving Data...")
        self.save_data(save_path, save_csv)
        self.log("Job Complete!", "SUCCESS")
        self.update_status("Idle")

    def save_data(self, path, save_csv):
        path_dir = os.path.dirname(path)
        if path_dir: os.makedirs(path_dir, exist_ok=True)
        json_file = path if path.endswith(".json") else f"{path}.json"
        with open(json_file, 'w') as f:
            json.dump(self.gathered_data, f, indent=4)
        self.log(f"Saved JSON to {json_file}", "SUCCESS")
        
        if save_csv and self.gathered_data:
            csv_file = path if path.endswith(".csv") else f"{path}.csv"
            try:
                df = pd.DataFrame.from_dict(self.gathered_data, orient='index')
                if "Release date" in df.columns: flat_df = df.pop("Release date")
                else: flat_df = pd.DataFrame()
                unpacked_df = flat_df
                
                cols = list(df.columns)
                for col in cols:
                    temp_series = df[col].dropna()
                    if temp_series.empty: continue
                    normalized = pd.json_normalize(list(temp_series))
                    normalized.index = temp_series.index
                    normalized.columns = [f"{col} - {c}" for c in normalized.columns]
                    unpacked_df = pd.concat([unpacked_df, normalized], axis=1)

                unpacked_df.to_csv(csv_file)
                self.log(f"Saved CSV to {csv_file}", "SUCCESS")
            except Exception as e:
                self.log(f"CSV Conversion Failed: {e}", "ERROR")


class ModernApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PhoneArena Scraper Pro 2025")
        self.geometry("1100x800")
        self.configure(bg=BG_COLOR)
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background=BG_COLOR)
        self.style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font=("Segoe UI", 10))
        self.style.configure("TButton", background=SEC_COLOR, foreground=FG_COLOR, borderwidth=0, font=("Segoe UI", 10))
        self.style.map("TButton", background=[('active', ACCENT_COLOR), ('disabled', '#444444')])
        self.style.configure("TCheckbutton", background=BG_COLOR, foreground=FG_COLOR)
        self.style.map("TCheckbutton", background=[('active', BG_COLOR)])
        self.style.configure("TLabelframe", background=BG_COLOR, foreground=ACCENT_COLOR, bordercolor=SEC_COLOR)
        self.style.configure("TLabelframe.Label", background=BG_COLOR, foreground=ACCENT_COLOR)
        self.style.configure("Horizontal.TProgressbar", background=ACCENT_COLOR, troughcolor=SEC_COLOR, bordercolor=BG_COLOR)

        self.vars = {
            "search": tk.StringVar(),
            "year_start": tk.StringVar(),
            "year_end": tk.StringVar(),
            "min_delay": tk.DoubleVar(value=2.0),
            "max_delay": tk.DoubleVar(value=5.0),
            "save_path": tk.StringVar(value="scraped_data"),
            "save_csv": tk.BooleanVar(value=True),
            "types": {},
            "status": tk.StringVar(value="Ready"),
            "man_status": tk.StringVar(value="Status: All Manufacturers (Default)"),
            "type_status": tk.StringVar(value="Status: All Types (Default)"),
            "year_status": tk.StringVar(value="Target: All Time")
        }
        
        self.manufacturers_all = sorted(available_filters["manufacturers"])
        self.setup_ui()
        
    def setup_ui(self):
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        left_pane = ttk.Frame(container, width=350)
        left_pane.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        right_pane = ttk.Frame(container)
        right_pane.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 1. MANUFACTURER SEARCH
        man_frame = ttk.LabelFrame(left_pane, text=" 1. MANUFACTURERS ", padding=10)
        man_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        lbl_man = ttk.Label(man_frame, textvariable=self.vars["man_status"], font=("Segoe UI", 9, "italic"))
        lbl_man.pack(fill=tk.X, pady=(0,5))
        
        search_box = ttk.Entry(man_frame, textvariable=self.vars["search"])
        search_box.pack(fill=tk.X, pady=(0, 5))
        search_box.bind("<KeyRelease>", self.filter_manufacturers)
        
        self.listbox = tk.Listbox(man_frame, selectmode=tk.MULTIPLE, bg=SEC_COLOR, fg=FG_COLOR, 
                                  highlightthickness=0, borderwidth=0, selectbackground=ACCENT_COLOR)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_man_select)
        
        sb = ttk.Scrollbar(man_frame, orient="vertical", command=self.listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=sb.set)
        
        self.refresh_list(self.manufacturers_all)
        
        btn_frame = ttk.Frame(man_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Select All", command=self.select_all_man).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Clear", command=self.clear_man).pack(fill=tk.X, pady=2)

        # 2. TYPE FILTER
        type_frame = ttk.LabelFrame(left_pane, text=" 2. DEVICE TYPES ", padding=10)
        type_frame.pack(fill=tk.X, pady=(0, 10))
        
        lbl_type = ttk.Label(type_frame, textvariable=self.vars["type_status"], font=("Segoe UI", 9, "italic"))
        lbl_type.pack(fill=tk.X, pady=(0,5))
        
        for dtype in available_filters["deviceType"]:
            v = tk.BooleanVar()
            self.vars["types"][dtype] = v
            v.trace("w", self.update_type_status)
            ttk.Checkbutton(type_frame, text=dtype, variable=v).pack(anchor="w")

        # 3. SETTINGS
        sets_frame = ttk.LabelFrame(left_pane, text=" 3. CONFIGURATION ", padding=10)
        sets_frame.pack(fill=tk.X)
        
        ttk.Label(sets_frame, text="Year Range:").pack(anchor="w")
        ttk.Label(sets_frame, textvariable=self.vars["year_status"], foreground=HINT_COLOR, font=("Segoe UI", 8)).pack(anchor="w", pady=(0,2))
        
        yf = ttk.Frame(sets_frame)
        yf.pack(fill=tk.X, pady=2)
        
        self.vars["year_start"].trace("w", self.update_year_status)
        self.vars["year_end"].trace("w", self.update_year_status)
        
        ttk.Entry(yf, textvariable=self.vars["year_start"], width=8).pack(side=tk.LEFT, padx=(0,5))
        ttk.Entry(yf, textvariable=self.vars["year_end"], width=8).pack(side=tk.LEFT)
        
        ttk.Label(sets_frame, text="Request Delay (sec):").pack(anchor="w", pady=(10,0))
        df = ttk.Frame(sets_frame)
        df.pack(fill=tk.X, pady=2)
        ttk.Spinbox(df, from_=0.5, to=60, textvariable=self.vars["min_delay"], width=5).pack(side=tk.LEFT, padx=(0,5))
        ttk.Label(df, text="to").pack(side=tk.LEFT, padx=2)
        ttk.Spinbox(df, from_=1, to=60, textvariable=self.vars["max_delay"], width=5).pack(side=tk.LEFT, padx=5)

        ttk.Label(sets_frame, text="Filename:").pack(anchor="w", pady=(10,0))
        sf = ttk.Frame(sets_frame)
        sf.pack(fill=tk.X)
        ttk.Entry(sf, textvariable=self.vars["save_path"]).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(sf, text="...", width=3, command=self.browse).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(sets_frame, text="Save as CSV", variable=self.vars["save_csv"]).pack(anchor="w", pady=5)

        # RIGHT PANE
        self.btn_run = tk.Button(right_pane, text="START SCRAPER", bg=ACCENT_COLOR, fg="black", 
                                 font=("Segoe UI", 11, "bold"), relief="flat", pady=8, command=self.start_thread)
        self.btn_run.pack(fill=tk.X, pady=(0, 10))

        log_frame = ttk.LabelFrame(right_pane, text=" SYSTEM LOGS ", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_widget = tk.Text(log_frame, bg=SEC_COLOR, fg="#FFFFFF", font=("Consolas", 9), 
                                  relief="flat", state="disabled")
        self.log_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        log_sb = ttk.Scrollbar(log_frame, command=self.log_widget.yview)
        log_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_widget.config(yscrollcommand=log_sb.set)

        prog_frame = ttk.Frame(right_pane)
        prog_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_lbl = ttk.Label(prog_frame, textvariable=self.vars["status"], foreground=SUCCESS_COLOR)
        self.status_lbl.pack(anchor="w", pady=(0, 5))
        
        # PROGRESS BAR 1: TOTAL
        ttk.Label(prog_frame, text="Total Job Progress:", font=("Segoe UI", 8)).pack(anchor="w")
        self.progress_total = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate")
        self.progress_total.pack(fill=tk.X, pady=(2, 8))

        # PROGRESS BAR 2: PAGE
        ttk.Label(prog_frame, text="Current Page Progress:", font=("Segoe UI", 8)).pack(anchor="w")
        self.progress_page = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate")
        self.progress_page.pack(fill=tk.X, pady=(2, 0))
        
        self.logger = RichLogger(self.log_widget)

    # DYNAMIC UI UPDATERS
    def on_man_select(self, event=None):
        count = len(self.listbox.curselection())
        if count == 0:
            self.vars["man_status"].set("Status: All Manufacturers (Default)")
        else:
            self.vars["man_status"].set(f"Status: {count} Selected")

    def update_type_status(self, *args):
        selected = [k for k,v in self.vars["types"].items() if v.get()]
        if not selected:
            self.vars["type_status"].set("Status: All Types (Default)")
        else:
            self.vars["type_status"].set(f"Status: {len(selected)} Types Selected")

    def update_year_status(self, *args):
        s = self.vars["year_start"].get().strip()
        e = self.vars["year_end"].get().strip()
        if not s and not e:
            self.vars["year_status"].set("Target: All Time")
        elif s and not e:
            self.vars["year_status"].set(f"Target: {s} Only")
        elif not s and e:
            self.vars["year_status"].set(f"Target: Up to {e}")
        else:
            self.vars["year_status"].set(f"Target: {s} to {e}")

    # CONTROLS FUNCS 
    def refresh_list(self, items):
        self.listbox.delete(0, tk.END)
        for i in items:
            self.listbox.insert(tk.END, i)
        self.on_man_select()

    def filter_manufacturers(self, event):
        term = self.vars["search"].get().lower()
        filtered = [m for m in self.manufacturers_all if term in m.lower()]
        self.refresh_list(filtered)

    def select_all_man(self):
        self.listbox.select_set(0, tk.END)
        self.on_man_select()

    def clear_man(self):
        self.listbox.selection_clear(0, tk.END)
        self.on_man_select()

    def browse(self):
        f = filedialog.asksaveasfilename(initialfile="phone_data", defaultextension=".json")
        if f: self.vars["save_path"].set(os.path.splitext(f)[0])

    def start_thread(self):
        sel_indices = self.listbox.curselection()
        sel_mans = [self.listbox.get(i) for i in sel_indices]
        
        sel_types = [t for t, v in self.vars["types"].items() if v.get()]
        if not sel_types: sel_types = None 
        
        ys = self.vars["year_start"].get().strip()
        ye = self.vars["year_end"].get().strip()
        years = []
        try:
            if ys: years.append(int(ys))
            if ye: years.append(int(ye))
        except ValueError:
             messagebox.showerror("Input Error", "Years must be numbers.")
             return

        if not years: years = None
        
        mn = self.vars["min_delay"].get()
        mx = self.vars["max_delay"].get()
        save = self.vars["save_path"].get()
        csv = self.vars["save_csv"].get()
        
        self.btn_run.config(state="disabled", text="RUNNING...", bg="#444444")
        self.progress_total['value'] = 0
        self.progress_page['value'] = 0
        self.log_widget.config(state="normal")
        self.log_widget.delete(1.0, tk.END)
        self.log_widget.config(state="disabled")
        
        t = threading.Thread(target=self.run_process, args=(sel_mans, years, sel_types, mn, mx, save, csv))
        t.daemon = True
        t.start()

    def run_process(self, mans, years, types, mn, mx, save, csv):
        logic = ScraperLogic(self.safe_log, self.safe_total, self.safe_page, self.safe_status, self.safe_toggle_mode)
        self.safe_log("Starting Scraper Service...", "INFO")
        try:
            logic.run(mans, years, types, mn, mx, save, csv)
        except Exception as e:
            self.safe_log(f"Critical Failure: {e}", "ERROR")
            self.safe_toggle_mode("determinate") # Stop bouncing on error
        self.after(0, lambda: self.btn_run.config(state="normal", text="START SCRAPER", bg=ACCENT_COLOR))

    # THREAD SAFE HELPERS
    def safe_log(self, msg, level="INFO"):
        self.after(0, lambda: self.logger.log(msg, level))
    def safe_total(self, val):
        self.after(0, lambda: self.progress_total.configure(value=val))
    def safe_page(self, val):
        self.after(0, lambda: self.progress_page.configure(value=val))
    def safe_status(self, txt):
        self.after(0, lambda: self.vars["status"].set(txt))
    def safe_toggle_mode(self, mode):
        # Handle switching between indeterminate (loading) and determinate (percentage)
        def _switch():
            if mode == "indeterminate":
                self.progress_total.configure(mode="indeterminate")
                self.progress_total.start(10)
            else:
                self.progress_total.stop()
                self.progress_total.configure(mode="determinate")
        self.after(0, _switch)

if __name__ == "__main__":
    app = ModernApp()
    app.mainloop()