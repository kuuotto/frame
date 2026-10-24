import json
import os
import random
import threading
import urllib.request

import RPi.GPIO as GPIO
from flask import Flask, flash, render_template, request
from inky.auto import auto
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename

# import generateInfo

displayLock = threading.Lock()

# Gpio button pins from top to bottom

# 5 == info
# 6 == rotate clockwise
# 16 == rotate counterclockwise
# 24 == reboot

BUTTONS = [5, 6, 16, 24]

# Set up RPi.GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Get the current path
PATH = os.path.dirname(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(PATH, "img")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

# Create the folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# setup eink display and border
inky_display = auto(ask_user=True, verbose=True)
inky_display.set_border(inky_display.BLACK)

app = Flask(__name__)


# handles button presses
def handleButton(pin):
    # top button
    if pin == 5:
        print("--A-- Pressed: [disabled]")
        # generateInfo.infoGen(inky_display.width, inky_display.height)
        # update the eink display
        # updateEinkAsync("infoImage.png", 0)
    elif pin == 6:
        print("--B-- Pressed: Rotate image clockwise")
        threading.Thread(target=rotateImage, args=(-90,), daemon=True).start()
    elif pin == 16:
        print("--C-- Pressed: Rotate image counter clockwise")
        threading.Thread(target=rotateImage, args=(90,), daemon=True).start()
    elif pin == 24:
        print("--D-- Pressed: Reboot the Pi")
        os.system("reboot")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def upload_file():

    if request.method == "POST":
        submit = request.form.get("submit")

        # browser upload button, or a bare API call like curl -F "file=@image.png"
        if submit == "Upload Image" or (not request.form and "file" in request.files):
            file = request.files.get("file")
            imageLink = request.form.get("text", "").strip()

            if file and allowed_file(file.filename):
                # delete current image
                deleteImage()

                # save the new image
                filename = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
                file.save(filename)

                # reset rotation
                writeSettingsFile(rotation=0)

                # update the display
                updateEinkAsync(filename)

                # send a response if upload was not through the website
                if not request.form:
                    return "File uploaded successfully", 200

            elif imageLink:
                try:
                    filename = imageLink.replace(":", "").replace("/", "").split("?")[0]
                    tmpPath = os.path.join(PATH, "download.tmp")

                    # download the new image
                    urllib.request.urlretrieve(imageLink, tmpPath)

                    # check that the downloaded object is a photo
                    with Image.open(tmpPath) as check:
                        check.verify()  # raises if it isn't a valid image

                    # delete the current image
                    deleteImage()

                    # move the temporary file
                    os.replace(tmpPath, os.path.join(UPLOAD_FOLDER, filename))

                    # reset rotation
                    writeSettingsFile(rotation=0)

                    # update the display
                    updateEinkAsync(filename)
                except Exception as e:
                    print(e)
                    flash("Error: Unsupported Media or Invalid Link!")

            else:
                flash("Error: Choose a file or enter an image link first!")

        # other button funcs
        # reboot
        if submit == "Reboot":
            print("reboot")
            os.system("reboot")

        # shutdown
        if submit == "Shutdown":
            print("shutdown")
            os.system("shutdown now")

        # rotate clockwise
        if submit == "rotateImage":
            print("rotating image")
            threading.Thread(target=rotateImage, args=(-90,), daemon=True).start()

        # ghosting clears
        if submit == "clearGhost":
            print("ghosting clear call!")
            threading.Thread(target=clearScreen, daemon=True).start()

        # save frame settings
        if submit == "Save Settings":
            writeSettingsFile(
                orientation="Horizontal"
                if request.form.get("frame_orientation") == "Horizontal Orientation"
                else "Vertical",
                adjust_aspect_ratio="checked"
                if request.form.get("adjust_ar") == "true"
                else "",
            )

            if image := currentImage():
                updateEinkAsync(image)

    arSwitchCheck, horizontalOrientationRadioCheck, verticalOrientationRadioCheck = (
        loadSettings()
    )
    return render_template(
        "main.html",
        horizontalOrientationRadioCheck=horizontalOrientationRadioCheck,
        verticalOrientationRadioCheck=verticalOrientationRadioCheck,
        arSwitchCheck=arSwitchCheck,
    )


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


def currentImage():
    files = os.listdir(UPLOAD_FOLDER)
    return files[0] if files else None


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
        img = ImageOps.exif_transpose(img).convert("RGB")  # respect photo rotation
        img = img.rotate(frameRotation + rotation, expand=True)

        # Fill vs. letterbox
        if settings.get("adjust_aspect_ratio") == "checked":
            # letterbox, show the whole photo
            img = ImageOps.pad(
                img, (inky_display.width, inky_display.height), color="white"
            )
        else:
            # crop to fill
            img = ImageOps.fit(img, (inky_display.width, inky_display.height))

        # Display the image
        inky_display.set_image(toInkyPalette(img))
        print("refreshing display...")
        inky_display.show()
        print("display done")


# clear the screen to prevent ghosting
def clearScreen():
    img = Image.new(
        mode="RGB",
        size=(inky_display.width, inky_display.height),
        color=(255, 255, 255),
    )

    with displayLock:
        inky_display.set_image(toInkyPalette(img))
        inky_display.show()

    if image := currentImage():
        updateEink(image)


def toInkyPalette(img, saturation=0.5):
    # inky's own conversion breaks on newer Pillow ("empty palette"), so quantize here
    palette = inky_display._palette_blend(saturation)
    paletteImg = Image.new("P", (1, 1))
    paletteImg.putpalette(palette + [0, 0, 0] * 248)
    return img.convert("RGB").quantize(
        palette=paletteImg, dither=Image.Dither.FLOYDSTEINBERG
    )


def deleteImage():
    for filename in os.listdir(UPLOAD_FOLDER):
        os.remove(os.path.join(UPLOAD_FOLDER, filename))

def rotateImage(deg):
    with settingsLock:
        rotation = (readSettingsFile().get("rotation", 0) + deg) % 360
        writeSettingsFile(rotation=rotation)

    if image := currentImage():
        updateEink(image)


# Add button event handlers
for pin in BUTTONS:
    GPIO.add_event_detect(pin, GPIO.FALLING, handleButton, bouncetime=250)

if __name__ == "__main__":
    app.secret_key = str(random.randint(100000, 999999))
    app.run(host="0.0.0.0", port=80)
