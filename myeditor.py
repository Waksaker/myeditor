# coding=utf-8
import os
import sys
import subprocess
import re  # ← tambah ini
import shutil

class SyntaxHighlighter:
    PY_PATTERNS = [
        ('KEYWORD', r'\b(and|as|assert|async|await|break|class|continue|def|del|elif|else|except|False|finally|for|from|global|if|import|in|is|lambda|None|nonlocal|not|or|pass|raise|return|True|try|while|with|yield|print)\b', '\033[34m'),
        ('STRING_SINGLE', r"'(?:\\.|[^'\\])*'", '\033[92m'),
        ('STRING_DOUBLE', r'"(?:\\.|[^"\\])*"', '\033[92m'),
        ('COMMENT', r'#.*$', '\033[38;5;245m'),
        ('NUMBER', r'\b\d+\.?\d*\b', '\033[91m'),
        ('FUNCTION', r'\b([a-zA-Z_]\w*)\s*\(', '\033[94m'),
    ]
    HTML_PATTERNS = [
        ('TAG', r'</?[a-zA-Z][a-zA-Z0-9-]*', '\033[34m'),
        ('CLOSE_TAG', r'>', '\033[34m'),
        ('ATTRIBUTE', r'\s([a-zA-Z-]+)=', '\033[91m'),
        ('VALUE', r'="[^"]*"', '\033[92m'),
        ('COMMENT', r'<!--.*?-->', '\033[38;5;245m'),
    ]

    @staticmethod  # ✅ DI DALAM kelas
    def get_file_type(filename):
        if not filename: return 'text'
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.py': return 'python'
        if ext in ['.html', '.htm']: return 'html'
        return 'text'

    @staticmethod  # ✅ DI DALAM kelas
    def highlight_line(line, file_type):
        if file_type == 'text': return line
        patterns = (SyntaxHighlighter.PY_PATTERNS if file_type == 'python'
                    else SyntaxHighlighter.HTML_PATTERNS)
        matches = []
        for _, pat, clr in patterns:
            for m in re.finditer(pat, line):
                matches.append((m.start(), m.end(), m.group(0), clr))
        matches.sort(key=lambda x: x[0])
        res, last = '', 0
        for s, e, txt, clr in matches:
            if s >= last:
                res += line[last:s] + clr + txt + '\033[0m'
                last = e
        res += line[last:]
        return res if res else line

# -- Warna ANSI --
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    GRAY = '\033[48;5;235;38;5;252m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# === Baca Papan Klip Sistem (tampal dari luar) ===
def get_clipboard_text():
    if os.name == 'nt':
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', 'Get-Clipboard -Raw'],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout
        except Exception:
            return ''
    return ''

if os.name == 'nt':
    os.system('color')
    import msvcrt
else:
    import tty, termios

# --- Baca Kekunci ---
if os.name == 'nt':
    def read_key():
        ch = msvcrt.getch()
        if ch in (b'\xe0', b'\x00'):
            ch2 = msvcrt.getch()
            keys = {
                b'H': 'UP', b'P': 'DOWN', b'K': 'LEFT', b'M': 'RIGHT',
                b'\r': 'ENTER', b'\x03': 'CTRL_C', b'\x16': 'CTRL_V',
                b'\x06': 'CTRL_F', b'\x12': 'CTRL_R', b'\x13': 'CTRL_S',
                b'\x11': 'CTRL_Q', b'\x08': 'BACKSPACE', b'\x7f': 'DELETE'
                # F3: b'\x74': 'F3'  ← tambah kalau nak guna F3
            }
            return keys.get(ch2, ch2.decode('utf-8', errors='ignore'))
        
        ctrl_map = {
            b'\x03': 'CTRL_C',   # Ctrl+C
            b'\x16': 'CTRL_V',   # Ctrl+V
            b'\x06': 'CTRL_F',   # Ctrl+F
            b'\x12': 'CTRL_R',   # Ctrl+R
            b'\x13': 'CTRL_S',   # Ctrl+S
            b'\x0E': 'CTRL_N',   # Ctrl+N = Fail Baru ✅
            b'\x15': 'CTRL_U',   # Ctrl+U = Ubah Nama ✅
            b'\x04': 'CTRL_D',   # Ctrl+D = Padam ✅
            b'\x11': 'CTRL_Q',   # Ctrl+Q = Keluar
            b'\r': 'ENTER',
            b'\x08': 'BACKSPACE'
        }
        return ctrl_map.get(ch, ch.decode('utf-8', errors='ignore'))
else:
    pass

class TerminalEditor:
    def __init__(self):
        self.cwd = os.getcwd()
        self.selected = 0
        self.scroll_offset = 0
        self.mode = 'browser'
        self.lines = []
        self.cursor_y = 0
        self.cursor_x = 0
        self.clipboard = ''
        self.filename = None
        self.dirty = False
        self.entries = []
        self.file_type = 'text'  # ← tambah ini

    def get_dir_list(self):
        self.entries = []
        try:
            for e in os.listdir(self.cwd):
                try:
                    full = os.path.join(self.cwd, e)
                    if os.path.isdir(full):
                        self.entries.append((e, True))
                    else:
                        self.entries.append((e, False))
                except Exception:
                    continue
        except Exception as e:
            self.entries = [('[RALAT] ' + str(e), False)]
        self.entries.sort(key=lambda x: (not x[1], x[0].lower()))
        return self.entries

    def draw_browser(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Colors.BOLD}{Colors.BLUE}📂 {self.cwd}{Colors.RESET}")
        print(f"{Colors.RED}{'-'*60}{Colors.RESET}")
        entries = self.get_dir_list()
        try:
            h = os.get_terminal_size().lines - 5
        except:
            h = 15
        if self.selected >= self.scroll_offset + h:
            self.scroll_offset = self.selected - h + 1
        if self.selected < self.scroll_offset:
            self.scroll_offset = self.selected

        if not entries:
            print("  (Tiada fail atau folder di dalam ini)")
        else:
            for i in range(self.scroll_offset, min(len(entries), self.scroll_offset + h)):
                nama, is_dir = entries[i]
                paparan = ('[DIR]  ' + nama) if is_dir else ('       ' + nama)
                if i == self.selected:
                    print(f"{Colors.GRAY}▶ {paparan}{Colors.RESET}")
                else:
                    if is_dir:
                        print(f"{Colors.GREEN}  {paparan}{Colors.RESET}")
                    else:
                        print(f"  {paparan}")
        print(f"{Colors.RED}{'-'*60}{Colors.RESET}")
        print(f"{Colors.BOLD}↑↓ Pilih | Enter Buka | Ctrl+U Ubah Nama | Ctrl+D Padam | Ctrl+N Fail Baru | Ctrl+Q Keluar{Colors.RESET}")

    def draw_editor(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        name = self.filename or '(fail baru)'
        tanda = f"{Colors.RED} * BELUM SIMPAN{Colors.RESET}" if self.dirty else ''
        print(f"{Colors.BOLD}{Colors.BLUE}📝 {name}{tanda}{Colors.RESET}")
        print(f"{Colors.RED}{'-'*60}{Colors.RESET}")
        try:
            h = os.get_terminal_size().lines - 6
        except:
            h = 15
        top = max(0, self.cursor_y - h + 1)
        for y in range(top, min(len(self.lines), top + h)):
            nombor = f"{y+1:3d}"
            baris = self.lines[y]
            
            # === Tambah Warna Sintaks ===
            baris_berwarna = SyntaxHighlighter.highlight_line(baris, self.file_type)
            
            if y == self.cursor_y:
                if self.cursor_x < len(baris):
                    bahagian_kiri = baris[:self.cursor_x]
                    huruf_kursor = baris[self.cursor_x]
                    bahagian_kanan = baris[self.cursor_x+1:]
                    teks_baris = f"{bahagian_kiri}\033[91;7m{huruf_kursor}\033[0m{bahagian_kanan}"
                else:
                    teks_baris = baris + "\033[91;7m \033[0m"
                print(f"{Colors.GRAY}▶ {nombor} │ {teks_baris}{Colors.RESET}")
            else:
                print(f"  {nombor} │ {baris_berwarna}{Colors.RESET}")
        print(f"{Colors.RED}{'-'*60}{Colors.RESET}")
        print(f"Ctrl+C Salin | Ctrl+V Tampal | Ctrl+F Cari | Ctrl+R Ganti | Ctrl+S Simpan | Ctrl+Q Kembali")

    def open_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
        except Exception as e:
            text = f"# Tidak boleh baca: {e}"
        self.lines = text.split('\n') if text else ['']
        self.filename = path
        self.file_type = SyntaxHighlighter.get_file_type(path)  # ← tambah ini
        self.cursor_y = 0
        self.cursor_x = 0
        self.dirty = False
        self.mode = 'editor'

    def save_file(self):
        if not self.filename:
            print(f"\n{Colors.RED}Nama fail: {Colors.RESET}", end='', flush=True)
            nama = sys.stdin.readline().strip()
            if not nama:
                return
            self.filename = os.path.join(self.cwd, nama)
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.lines))
            self.dirty = False
            self.file_type = SyntaxHighlighter.get_file_type(self.filename)
        except Exception as e:
            print(f"{Colors.RED}Ralat simpan: {e}{Colors.RESET}")

    def new_file(self):
        """Buat fail baru kosong & masuk mod editor"""
        self.lines = ['']
        self.filename = None
        self.file_type = 'text'
        self.cursor_y = 0
        self.cursor_x = 0
        self.dirty = False
        self.mode = 'editor'

    def rename_entry(self):
        """Ubah nama fail/folder yang dipilih"""
        entries = self.get_dir_list()
        if not entries:
            return
        nama_lama, is_dir = entries[self.selected]
        laluan_lama = os.path.join(self.cwd, nama_lama)

        print(f"\n{Colors.RED}Ubah nama: {nama_lama}{Colors.RESET}")
        print(f"Nama baru: ", end='', flush=True)
        nama_baru = sys.stdin.readline().strip()

        if not nama_baru or nama_baru == nama_lama:
            return

        laluan_baru = os.path.join(self.cwd, nama_baru)
        try:
            os.rename(laluan_lama, laluan_baru)
            print(f"{Colors.GREEN}Berhasil!{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}Gagal: {e}{Colors.RESET}")
        input("Tekan Enter...")

    def delete_entry(self):
        """Padam fail atau folder yang dipilih"""
        entries = self.get_dir_list()
        if not entries:
            return
        
        nama_lama, is_dir = entries[self.selected]
        laluan = os.path.join(self.cwd, nama_lama)
        
        # Minta pengesahan sebelum padam
        jenis = "folder" if is_dir else "fail"
        print(f"\n{Colors.RED}Pasti nak padam {jenis}: {nama_lama}? (Y/N){Colors.RESET}")
        sah = sys.stdin.readline().strip().upper()
        
        if sah != 'Y':
            print(f"{Colors.RED}Dibatalkan.{Colors.RESET}")
            input("Tekan Enter...")
            return
        
        try:
            if is_dir:
                shutil.rmtree(laluan)  # Boleh padam folder tak kosong
            else:
                os.remove(laluan)
            print(f"{Colors.GREEN}Berhasil dipadam!{Colors.RESET}")
        except Exception as e:
            if is_dir:
                print(f"{Colors.RED}Gagal: Folder mungkin tidak kosong{Colors.RESET}")
            else:
                print(f"{Colors.RED}Gagal: {e}{Colors.RESET}")
        
        input("Tekan Enter...")

    def insert_char(self, ch):
        line = self.lines[self.cursor_y]
        self.lines[self.cursor_y] = line[:self.cursor_x] + ch + line[self.cursor_x:]
        self.cursor_x += 1
        self.dirty = True

    def paste_text(self, teks):
        """Tampal teks dari papan klip, ikut kedudukan kursor"""
        baris_aktif = self.lines[self.cursor_y]
        kiri = baris_aktif[:self.cursor_x]
        kanan = baris_aktif[self.cursor_x:]
        bahagian = teks.split('\n')
        bahagian[0] = kiri + bahagian[0]
        bahagian[-1] = bahagian[-1] + kanan
        self.lines[self.cursor_y:self.cursor_y+1] = bahagian
        self.cursor_y += len(bahagian) - 1
        self.cursor_x = len(bahagian[-1])
        self.dirty = True

    def handle_editor_key(self, key):
        if key == 'CTRL_S':
            self.save_file()
        elif key == 'CTRL_Q':
            self.mode = 'browser'
            self.filename = None
            self.lines = []
            self.file_type = 'text'  # ← tambah ini
        elif key == 'CTRL_C':
            self.clipboard = self.lines[self.cursor_y]
        elif key == 'CTRL_V':
            # Baca dari papan klip sistem + tampal
            teks_luar = get_clipboard_text()
            if teks_luar:
                self.paste_text(teks_luar)
            elif self.clipboard:
                for ch in self.clipboard:
                    self.insert_char(ch)
        elif key == 'CTRL_F':
            cari = input("\nCari: ")
            if cari:
                jumpa = [(i, self.lines[i].find(cari)) for i in range(len(self.lines)) if cari in self.lines[i]]
                if jumpa:
                    self.cursor_y, self.cursor_x = jumpa[0]
                else:
                    print(f"{Colors.RED}Tidak dijumpai{Colors.RESET}")
                    input("Tekan Enter...")
        elif key == 'CTRL_R':
            cari = input("\nCari apa: ")
            ganti = input("Ganti dengan: ")
            if cari:
                bilangan = sum(line.count(cari) for line in self.lines)
                for i in range(len(self.lines)):
                    self.lines[i] = self.lines[i].replace(cari, ganti)
                self.dirty = True
                print(f"{Colors.GREEN}Diganti {bilangan} tempat{Colors.RESET}")
                input("Tekan Enter...")
        elif key == 'UP':
            if self.cursor_y > 0:
                self.cursor_y -= 1
                self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))
        elif key == 'DOWN':
            if self.cursor_y < len(self.lines) - 1:
                self.cursor_y += 1
                self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))
        elif key == 'LEFT':
            if self.cursor_x > 0:
                self.cursor_x -= 1
            elif self.cursor_y > 0:
                self.cursor_y -= 1
                self.cursor_x = len(self.lines[self.cursor_y])
        elif key == 'RIGHT':
            if self.cursor_x < len(self.lines[self.cursor_y]):
                self.cursor_x += 1
            elif self.cursor_y < len(self.lines) - 1:
                self.cursor_y += 1
                self.cursor_x = 0
        elif key == 'ENTER':
            line = self.lines[self.cursor_y]
            self.lines[self.cursor_y] = line[:self.cursor_x]
            self.lines.insert(self.cursor_y + 1, line[self.cursor_x:])
            self.cursor_y += 1
            self.cursor_x = 0
            self.dirty = True
        elif key == 'BACKSPACE':
            line = self.lines[self.cursor_y]
            if self.cursor_x > 0:
                self.lines[self.cursor_y] = line[:self.cursor_x-1] + line[self.cursor_x:]
                self.cursor_x -= 1
                self.dirty = True
            elif self.cursor_y > 0:
                self.cursor_x = len(self.lines[self.cursor_y - 1])
                self.lines[self.cursor_y - 1] += self.lines.pop(self.cursor_y)
                self.cursor_y -= 1
                self.dirty = True
        elif len(key) == 1:
            self.insert_char(key)

    def handle_browser_key(self, key):
        entries = self.get_dir_list()
        if key == 'UP':
            self.selected = max(0, self.selected - 1)
        elif key == 'DOWN':
            self.selected = min(len(entries) - 1, self.selected + 1)
        elif key == 'ENTER':
            if not entries:
                return
            nama, is_dir = entries[self.selected]
            laluan = os.path.join(self.cwd, nama)
            if is_dir:
                self.cwd = laluan
                self.selected = 0
                self.scroll_offset = 0
            else:
                self.open_file(laluan)
        elif key == 'CTRL_N':
            self.new_file()
        elif key == 'CTRL_U':  # Guna Ctrl+U ganti F2
            self.rename_entry()
        elif key == 'CTRL_D':   # Padam — guna Ctrl+D
            self.delete_entry()
        elif key == 'LEFT' or key == 'BACKSPACE':
            induk = os.path.dirname(self.cwd)
            if induk != self.cwd:
                self.cwd = induk
                self.selected = 0
                self.scroll_offset = 0
        elif key == 'CTRL_Q':
            sys.exit(0)

    def run_windows(self):
        while True:
            if self.mode == 'browser':
                self.draw_browser()
            else:
                self.draw_editor()
            key = read_key()
            if self.mode == 'browser':
                self.handle_browser_key(key)
            else:
                self.handle_editor_key(key)

    def run_unix(self):
        stdin_fd = sys.stdin.fileno()
        lama = termios.tcgetattr(stdin_fd)
        try:
            tty.setraw(stdin_fd)
            while True:
                if self.mode == 'browser':
                    self.draw_browser()
                else:
                    self.draw_editor()
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    seq = sys.stdin.read(2)
                    peta = {'[A':'UP', '[B':'DOWN', '[C':'RIGHT', '[D':'LEFT'}
                    key = peta.get(seq, ch)
                elif ch in '\r\n':
                    key = 'ENTER'
                elif ch == '\x03': key = 'CTRL_C'
                elif ch == '\x04': key = 'CTRL_D'
                elif ch == '\x16': key = 'CTRL_V'
                elif ch == '\x06': key = 'CTRL_F'
                elif ch == '\x12': key = 'CTRL_R'
                elif ch == '\x13': key = 'CTRL_S'
                elif ch == '\x11': key = 'CTRL_Q'
                elif ch in '\x7f\b': key = 'BACKSPACE'
                else:
                    key = ch
                if self.mode == 'browser':
                    self.handle_browser_key(key)
                else:
                    self.handle_editor_key(key)
        finally:
            termios.tcsetattr(stdin_fd, termios.TCSADRAIN, lama)

    def run(self):
        if os.name == 'nt':
            self.run_windows()
        else:
            self.run_unix()

if __name__ == '__main__':
    app = TerminalEditor()
    app.run()