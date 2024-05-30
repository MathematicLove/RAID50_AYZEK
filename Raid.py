import os


def hex_xor(hex_str1, hex_str2):
    hex_str1 = str(hex_str1)
    hex_str2 = str(hex_str2)
    hex_str1 = hex_str1.replace('R', '0') #если вдруг нули
    hex_str2 = hex_str2.replace('R', '0')
    num1 = int(hex_str1, 16)
    num2 = int(hex_str2, 16)
    xor_result = num1 ^ num2
    xor_hex_str = format(xor_result, 'x')
    return xor_hex_str

class Raid50:
    def __init__(self, base_path, num_disks=10, group_size=5, max_layers=64): #диски #группы (чанки) #абобус 64
        #5 = 2 + 2 + 1 избыт
        self.num_disks = num_disks
        self.group_size = group_size
        self.max_layers = max_layers
        self.base_path = base_path
        self.groups = [Raid5(base_path, i, group_size, max_layers) for i in range(num_disks // group_size)]
    
    def write(self, data, index):
        if len(data) != 10:
            print("Строка должна быть в 10 символов!.")
            return
        if index >= self.max_layers:
            print(f"Ошибка! адресс должен быть в пределах нуля до {self.max_layers-1}")
            return
        chunk1 = data[:5]
        chunk2 = data[5:]
        self.groups[0].write(chunk1, index)
        self.groups[1].write(chunk2, index)
    
    def read(self, index):
        if index >= self.max_layers:
            print(f"Ошибка! адресс должен быть в пределах нуля до {self.max_layers-1}")
            return None
        data1 = self.groups[0].read(index)
        data2 = self.groups[1].read(index)
        if not data1 and not data2:
            return "Диски пусты."
        cdata = data1 + data2
        return cdata

    def recover(self):
        for group in self.groups:
            group.recover()

    def reset(self):
        for group in self.groups:
            group.reset()

    def get_written_indices(self):
        written_indices = set()
        for group in self.groups:
            written_indices.update(group.get_written_indices())
        return sorted(list(written_indices))

class Raid5:
    def __init__(self, base_path, group_index, num_disks, max_layers):
        self.num_disks = num_disks
        self.data_disks = num_disks - 1
        self.base_path = base_path
        self.group_index = group_index
        self.max_layers = max_layers
        self.files = [os.path.join(base_path, f"disk{i + (group_index*5)}.txt") for i in range(num_disks)]
        for file in self.files:
            if not os.path.exists(file):
                with open(file, 'w') as f:
                    f.write('\n' * max_layers)

    def write(self, data, layer):
        if len(data) != 5:
            print("Ошибка! Должно быть в 5 байтов.")
            return
        
        parts = [data[:2], data[2:3], data[3:4], data[4:5]] # Для того что б 1 был иЗбЫтОчНыЙ
        parity = "00"
        for part in parts:
            parity = hex_xor(parity,part)
        
        parity_index = (self.num_disks - 1 - (layer % self.num_disks)) % self.num_disks

        for i in range(self.num_disks):
            with open(self.files[i], 'r+') as f:
                lines = f.readlines()
                if i == parity_index:
                    lines[layer] = parity + '\n'
                else:
                    lines[layer] = parts.pop(0).rjust(2, 'R') + '\n'
                f.seek(0)
                f.writelines(lines)

    def read(self, layer):
        data = []
        parity_index = (self.num_disks - 1 - (layer % self.num_disks)) % self.num_disks
        for i in range(self.num_disks):
            if i == parity_index:
                continue
            try:
                with open(self.files[i], 'r') as f:
                    lines = f.readlines()
                    if len(lines) > layer:
                        data.append(lines[layer].replace('R', '').strip())
            except FileNotFoundError:
                continue
        cdata = ''.join(data) if data else None 
        return str(cdata) if data else None

    def recover(self):
        for i in range(self.num_disks):
            if self.is_disk_failed(i):
                self.rebuild_disk(i)

    def is_disk_failed(self, disk_index):
        return not os.path.exists(self.files[disk_index])

    def rebuild_disk(self, disk_index):
        linescor = self.get_written_indices()
        disk_size = len(linescor)
        rebuilt_data = [""] * self.max_layers
        for pos in linescor:
            parity_index = (self.num_disks - 1 - (pos % self.num_disks)) % self.num_disks
            if disk_index == parity_index:
                parity = "00"
                for i in range(self.num_disks):
                    try:
                        with open(self.files[i], 'r') as f:
                            lines = f.readlines()
                            if len(lines) > pos:
                                data = lines[pos].strip()
                                if data == "\n" : 
                                    parity = "\n"
                                    break
                                parity = hex_xor(parity, data)
                    except FileNotFoundError:
                        continue
                rebuilt_data[pos] = parity
            else:
                parity = "00"
                for i in range(self.num_disks):
                    try:
                        with open(self.files[i], 'r') as f:
                            lines = f.readlines()
                            if len(lines) > pos:
                                data = lines[pos].strip()
                                if data == "\n" : 
                                    parity = "\n"
                                    break
                                parity = hex_xor(parity, data)
                    except FileNotFoundError:
                        continue
                rebuilt_data[pos] = parity
        
        with open(self.files[disk_index], 'w') as f:
            f.write('\n'.join(rebuilt_data) + '\n')

    def reset(self):
        for file in self.files:
            with open(file, 'w') as f:
                f.write('\n' * self.max_layers)
    
    def get_written_indices(self):
        written_indices = set()
        try :
            with open(self.files[0], 'r') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                     if line.strip():
                        written_indices.add(i)
        except  :
             with open(self.files[1], 'r') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                     if line.strip():
                        written_indices.add(i)
        return written_indices

def menu():
    base_path = './raid_disks'
    os.makedirs(base_path, exist_ok=True)
    raid50 = Raid50(base_path)

    while True:
        print("Меню:")
        print("1) Записать в диски")
        print("2) Прочесть инфу")
        print("3) Восстонавить диски")
        print("4) Удалить все")
        print("5) Выйти")
        choice = input("Выберите пункт меню: ")

        if choice == "1":
            data = input("Введите строку в 10 символов: ")
            if len(data) != 10:
                print("Ошибка! Строка должна быть в 10 байт.")
                continue
            index = int(input(f"Введите индекс от нуля до {raid50.max_layers - 1}: "))
            if index < 0:
                print("Ошибка! Индекс должен быть больше нуля!")
                continue
            else:
                raid50.write(data, index)
            continue
        elif choice == "2":
            written_indices = raid50.get_written_indices()
            if not written_indices:
                print("Диски пусты.")
            else:
                print(f"Тут есть что-то: {written_indices}")
                index = int(input(f"Введите одно из представленных индексов: "))
                if index not in written_indices:
                    print("Не верно введен индекс.")
                    continue
                result = raid50.read(index)
                print(result)
        elif choice == "3":
            raid50.recover()
            print("Восстонавление завершено!")
        elif choice == "4":
            raid50.reset()
            print("Удалено!")
        elif choice == "5":
            break
        else:
            print("Введите цифру которая есть в меню.")

if __name__ == "__main__":
    menu()
