import tkinter as tk
from tkinter import scrolledtext, font
from emu import act

vfs_name = 'home$'

class TerminalGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(vfs_name)
        self.root.geometry("800x600")

        # Настройка шрифта
        self.terminal_font = font.Font(family="Courier New", size=12)

        # Создание текстовой области для вывода
        self.output_area = scrolledtext.ScrolledText(
            root,
            wrap=tk.WORD,
            font=self.terminal_font,
            bg="black",
            fg="white",
            insertbackground="white"
        )
        self.output_area.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        self.output_area.config(state=tk.DISABLED)

        # Создание рамки для ввода команды
        input_frame = tk.Frame(root, bg="black")
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        # Метка с приглашением к вводу
        self.prompt_label = tk.Label(
            input_frame,
            text="home$ ",
            font=self.terminal_font,
            bg="black",
            fg="green",
            anchor="w"
        )
        self.prompt_label.pack(side=tk.LEFT)

        # Поле ввода команды
        self.command_entry = tk.Entry(
            input_frame,
            font=self.terminal_font,
            bg="black",
            fg="white",
            insertbackground="white",
            width=50
        )
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.command_entry.bind("<Return>", self.execute_command)
        self.command_entry.focus_set()

    def print_output(self, text):
        """Вывод текста в текстовую область"""
        self.output_area.config(state=tk.NORMAL)
        self.output_area.insert(tk.END, text)
        self.output_area.see(tk.END)
        self.output_area.config(state=tk.DISABLED)

    def execute_command(self, event):
        """Обработка выполнения команды"""
        command = self.command_entry.get().strip()
        self.command_entry.delete(0, tk.END)

        # Выводим команду в текстовую область
        self.print_output(f"home$ {command}\n")

        # Обрабатываем команду с помощью функции act()
        result = act(command)

        # Если команда exit - закрываем приложение
        if command == 'exit':
            self.root.quit()
        # Если есть результат - выводим его
        elif result:
            self.print_output(f"{result}\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = TerminalGUI(root)
    root.mainloop()