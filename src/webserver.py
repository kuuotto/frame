import urllib.request
import os,random
from flask import Flask, flash, request,render_template
from werkzeug.utils import secure_filename
from flask import send_from_directory
import json
from inky.auto import auto
import RPi.GPIO as GPIO
from PIL import Image,ImageOps 
import generateInfo
import threading

displayLock = threading.Lock()

# Gpio button pins from top to bottom

#5 == info
#6 == rotate clockwise
#16 == rotate counterclockwise
#24 == reboot

BUTTONS = [5, 6, 16, 24]

#Set up RPi.GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Get the current path
PATH = os.path.dirname(os.path.dirname(__file__))
print(PATH)
UPLOAD_FOLDER = os.path.join(PATH, "img")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg','webp'}
print(ALLOWED_EXTENSIONS)

# Check whether the specified path exists or not
if not os.path.exists(UPLOAD_FOLDER):
   os.makedirs(UPLOAD_FOLDER)

#setup eink display and border
inky_display = auto(ask_user=True, verbose=True)
inky_display.set_border(inky_display.BLACK)

app = Flask(__name__)

#handles button presses
def handleButton(pin):
    #top button
    if(pin == 5):
        print("--A-- Pressed: Show PiInk info")
        generateInfo.infoGen(inky_display.width,inky_display.height)
        #update the eink display
        updateEinkAsync("infoImage.png", 0)
    elif(pin == 6):
        print("--B-- Pressed: Rotate image clockwise")
        threading.Thread(target=rotateImage, args=(-90,), daemon=True).start()
    elif(pin == 16):
        print("--C-- Pressed: Rotate image counter clockwise")
        threading.Thread(target=rotateImage, args=(90,), daemon=True).start()
    elif(pin == 24):
        print("--D-- Pressed: Reboot the Pi")
        os.system('sudo reboot')  

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    print("req ", request.files)    

    arSwitchCheck, horizontalOrientationRadioCheck, verticalOrientationRadioCheck = loadSettings()
    
    if request.method == 'POST':
        
        #print(request.form)
        #upload via link, add support in for api calls like cURL 'curl -X POST -F "file=@image.png" piink.local'
        if 'file' in request.files or (request.form and request.form.get("submit") == "Upload Image"):
            file = request.files['file']
            print(file)
            if file and allowed_file(file.filename):
                deleteImage()
                filename = secure_filename(file.filename)
                filename = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filename)

                # reset rotation
                writeSettingsFile(rotation = 0)

                # update the display
                updateEinkAsync(filename)

                if(len(request.form) == 0):
                    return "File uploaded successfully", 200
            else:
                deleteImage()
                imageLink = request.form.getlist("text")[0]
                print(imageLink)
                try:
                    filename = imageLink.replace(":","").replace("/","")
                    filename = filename.split("?")[0]
                    print(filename)
                    #grab the url and download it to the folder
                    urllib.request.urlretrieve(imageLink, os.path.join(UPLOAD_FOLDER, filename))

                    # reset rotation
                    writeSettingsFile(rotation = 0)

                    # update the display
                    updateEinkAsync(filename)
                except:
                    #flash error message
                    flash("Error: Unsupported Media or Invalid Link!")
                    return render_template('main.html')
                    
        #other button funcs
        #reboot
        if request.form["submit"] == 'Reboot':
            print("reboot")
            os.system("sudo reboot")
        
        #shutdown
        if request.form["submit"] == 'Shutdown':
            print("shutdown")
            os.system("sudo shutdown")

        #rotate clockwise
        if request.form["submit"] == 'rotateImage':
            print("rotating image")
            threading.Thread(target=rotateImage, args=(-90,), daemon=True).start()

        #ghosting clears
        if request.form["submit"] == 'clearGhost':
            print("ghosting clear call!")
            threading.Thread(target=clearScreen, daemon=True).start()

        #save frame settings
        if request.form["submit"] == 'Save Settings':
            if(request.form["frame_orientation"] == "Horizontal Orientation"):
                horizontalOrientationRadioCheck = "checked"
                verticalOrientationRadioCheck = ""
            else:
                horizontalOrientationRadioCheck = ""
                verticalOrientationRadioCheck = "checked"
            try:
                if request.form["adjust_ar"] == "true":
                    arSwitchCheck = "checked"
            except:
                arSwitchCheck = ""
                pass
            saveSettings(horizontalOrientationRadioCheck,verticalOrientationRadioCheck,arSwitchCheck)
            updateEinkAsync(os.listdir(UPLOAD_FOLDER)[0])
            return render_template('main.html',horizontalOrientationRadioCheck = horizontalOrientationRadioCheck,verticalOrientationRadioCheck=verticalOrientationRadioCheck,arSwitchCheck=arSwitchCheck)       
    return render_template('main.html',horizontalOrientationRadioCheck = horizontalOrientationRadioCheck,verticalOrientationRadioCheck=verticalOrientationRadioCheck,arSwitchCheck=arSwitchCheck)

SETTINGS_FILE = os.path.join(PATH, "config/settings.json")
settingsLock = threading.RLock()

def readSettingsFile():
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}

def writeSettingsFile(**changes):
    with settingsLock:
        data = readSettingsFile()
        data.update(changes)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f)

def loadSettings():
    settingsData = readSettingsFile()
    arSwitchCheck = settingsData.get("adjust_aspect_ratio", "")
    if settingsData.get("orientation") == "Horizontal":
        return arSwitchCheck, "checked", ""
    return arSwitchCheck, "", "checked"

def saveSettings(orientationHorizontal,orientationVertical,adjustAR):
    orientationSetting = "Horizontal" if orientationHorizontal == "checked" else "Vertical"
    writeSettingsFile(orientation=orientationSetting, adjust_aspect_ratio=adjustAR)

def updateEinkAsync(*args):
    threading.Thread(target=updateEink, args=args, daemon=True).start()

def updateEink(filename, rotation=None):
    settings = readSettingsFile()
    # how the frame is oriented: in portait the eink is rotated 90deg, in
    # landscape 180deg
    frameRotation = 180 if settings.get("orientation") == "Horizontal" else 90
    if rotation is None:
        rotation = settings.get("rotation", 0)

    with displayLock, Image.open(os.path.join(UPLOAD_FOLDER, filename)) as img:
        # decode JPEGs at reduced size for faster processing
        img.draft("RGB", (inky_display.width * 2, inky_display.height * 2))

        # Rotation
        img = ImageOps.exif_transpose(img).convert("RGB") # respect photo rotation
        img = img.rotate(frameRotation + rotation, expand=True)

        # Fill vs. letterbox
        if settings.get("adjust_aspect_ratio") == "checked":
            # letterbox, show the whole photo
            img = ImageOps.pad(img, (inky_display.width, inky_display.height), color = "white")
        else:
            # crop to fill
            img = ImageOps.fit(img, (inky_display.width, inky_display.height))

        # Display the image
        inky_display.set_image(toInkyPalette(img))
        inky_display.show()

#clear the screen to prevent ghosting
def clearScreen():
    print("running ghost clear")
    img = Image.new(mode="RGB", size=(inky_display.width, inky_display.height),color=(255,255,255))

    with displayLock:
        inky_display.set_image(toInkyPalette(img))
        inky_display.show()

    updateEink(os.listdir(UPLOAD_FOLDER)[0])

def toInkyPalette(img, saturation=0.5):
    # inky's own conversion breaks on newer Pillow ("empty palette"), so quantize here
    palette = inky_display._palette_blend(saturation)
    paletteImg = Image.new("P", (1, 1))
    paletteImg.putpalette(palette + [0, 0, 0] * 248)
    return img.convert("RGB").quantize(palette=paletteImg, dither=Image.Dither.FLOYDSTEINBERG)

def deleteImage():
    for filename in os.listdir(UPLOAD_FOLDER):
        fp = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(fp):
            os.remove(fp)
            
def rotateImage(deg):
    with settingsLock:
        rotation = (readSettingsFile().get("rotation", 0) + deg) % 360
        writeSettingsFile(rotation=rotation)

    updateEink(os.listdir(UPLOAD_FOLDER)[0])

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER,filename)


#run button checks on gpio    
for pin in BUTTONS:
    print(pin)    
    GPIO.add_event_detect(pin, GPIO.FALLING, handleButton, bouncetime=250)
    
if __name__ == '__main__':
    app.secret_key = str(random.randint(100000,999999))
    app.run(host="0.0.0.0",port=80)
