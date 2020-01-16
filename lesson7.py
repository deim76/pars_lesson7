import shutil
import threading

import pytesseract
from PIL import Image
import time
import os
from queue import Queue

from pymongo import MongoClient

import PyPDF2

class Elements:
    def __init__(self,path,image_path,num_page):
        self.path=path
        self.image_path=image_path
        self.num_page=num_page


class Thread_OCR(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):

        extruct_number(self.queue.get())
        self.queue.task_done()





path_pdf = 'PDF'
path_jpg = 'JPG'
path_dir='СКД_Поверка весов'

# todo сортировка PDF JPG по папкам
def sort_files(listdir):
    if len(listdir)!= 0:
       path_dir=listdir[0]
       listdir.remove(path_dir)
    else:
        return

    list_files=os.listdir(path_dir)
    for file in list_files:
        if file.split('.')[-1] == 'pdf':
           shutil.copy(path_dir+'\\'+file,path_pdf,)

        elif file.split('.')[-1] == 'jpg':
            shutil.copy(path_dir + '\\' + file, path_jpg)

        else:
           if os.path.isdir(path_dir+'\\'+file):
             listdir.append(path_dir+'\\'+file)

    sort_files(listdir)

# todo извлечение JPG из PDF
def extruct_jpg_from_pdf(file_path):
    try:
        pdf_file = PyPDF2.PdfFileReader(open(file_path, 'rb'), strict=False)
    except PyPDF2.utils.PdfReadError as e:
        shutil.copy(file_path, 'error-files')

    list_images=[]
    for page_num in range(0, pdf_file.getNumPages()):
        page = pdf_file.getPage(page_num)
        page_object=page['/Resources']['/XObject'].getObject()
        if page_object['/Im0'].get('/Subtype')=='/Image':
            data = page_object['/Im0']._data
            # size = (page_object['/Im0']['/Width'], page_object['/Im0']['/Height'])
            # if page_object['/Im0'].get('/ColorSpace')=='/DeviceRGB':
            #     mode = 'RGB'
            # else:
            #     mode='P'
            if  page_object['/Im0'].get('/Filter')=='/DCTDecode':
                files_type = 'jpg'
            elif page_object['/Im0'].get('/Filter')=='/FlatDecode':
                files_type = 'png'
            elif page_object['/Im0'].get('/Filter')=='/JPXDecode':
                files_type = 'jp2'

            image_name=f'{file_path.split("/")[-1]}-{time.time()}-{page_num}.{files_type}'
            image=open(image_name,'wb')
            image.write(data)
            image.close()
            element=Elements(file_path,image_name,page_num)
            list_images.append(element)

    queue = Queue()
    queue.put(list_images)
    t = Thread_OCR(queue)
    t.setDaemon(True)
    t.start()
    print(queue.join())
    #extruct_number(list_images)

def extruct_number(list_images):
    for element in list_images:
        img_obj = Image.open(element.image_path)
        text=pytesseract.image_to_string(img_obj,'rus')
        template=['заводской (серийный) номер','заводской номер (номера)']
        if text.lower().find(template[0])+1 or text.lower().find(template[1])+1 :
           for idx, line in enumerate(text.split('\n')):
               if line.lower().find(template[0])+1 or line.lower().find(template[1])+1:
                   #eng_text=pytesseract.image_to_string(img_obj,'eng').split('\n')[idx]
                   if line.find('!')+1:
                       for pn,i in enumerate(line.split('!')):
                           number = i.split(' ')[-1]
                           if number:
                                write_string_db(element, number)
                   else:
                           number=line.split(' ')[-1]
                           if number:
                                write_string_db(element, number)

    #   os.remove(image_name)

def write_string_db(element,number):
    collection.insert_one({'Image_path':element.path,
                       "Page_number":element.num_page,
                       'Number':number})


bd_url = 'mongodb://localhost:27017/'

client = MongoClient(bd_url)
db = client['serial_number']
collection = db['serial_number']
listdir=[path_dir]
sort_files(listdir)

list_elements=[]
for idx,file in enumerate(os.listdir(path_jpg)):
    list_elements.append(Elements(path_jpg+'\\'+file,path_jpg+'\\'+file,1))
extruct_number(list_elements)

for file in os.listdir(path_pdf):
    try:
        extruct_jpg_from_pdf(path_pdf+'\\'+file)
    except:
        shutil.copy(path_pdf+'\\'+file, 'error-files')





