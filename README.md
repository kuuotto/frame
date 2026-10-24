<h1 align="center">PiInk - A Raspberry Pi Powered E-Ink Picture Frame</h1>

![all 3 piinks](https://github.com/tlstommy/PiInk/assets/36305669/9531da45-1ef7-40e7-9d1f-2fef53ca01f3)


### An open-source, low-power, digital picture frame that gives images a natural, paper-like, aesthetic.

**Features:**
- **Web UI**: A built-in interface to control PiInk and upload images over the network.
- **Low Power**: The E-Ink display only needs power to change images, allowing pictures to persist on the frame.
- **Natural Aesthetic**: No backlight and the unique E-Ink technology make images look as if they are printed onto paper.
- **Open Source**: PiInk is under the MIT License, so modify it as you see fit!

# Table of Contents
* [Overview](#piink---a-raspberry-pi-powered-e-ink-picture-frame)
* [Installation](#installation)
* [WebUI & PiInk Buttons](#webui--piink-buttons)
* [Parts List](#parts-list)
   * [E-Ink Display](#e-ink-display)
   * [3D Printed Stand](#3d-printed-stand)
* [Frame Assembly](#piink-frame-assembly)
* [Demo](#demo)
* [Issues & Suggestions](#issues--suggestions)


# Installation

To install, clone the repository, run the install script, and follow the on-screen instructions:

```bash
git clone https://github.com/tlstommy/PiInk.git
cd PiInk
sudo bash install.sh

```

Upon reboot, the PiInk program will start and be accessible on the web at the Raspberry Pi's IP address or at `piink.local` 

# System service

To check whether the `piink` system service is running:
```bash
sudo systemctl status piink.service
```

To check the logs:
```bash
journalctl -u piink.service -f
```

To disable the system service (so it doesn't start on boot):
```bash
sudo systemctl disable piink
```

To enable the system service:
```bash
sudo systemctl enable piink
```

To start the system service:
```bash
sudo systemctl start piink
```

To stop the system service (it will still restart on next boot):
```bash
sudo systemctl stop piink
```

To restart the system service:
```bash
sudo systemctl restart piink
```

# WebUI & PiInk Buttons

**The PiInk can be controlled via the WebUI which can be found at the Raspberry Pi's IP address or at `piink.local`**

![webui](https://github.com/tlstommy/PiInk/assets/36305669/e0531d93-8249-4087-9238-81d80839c5b8)



### Uploading an image
Use the WebUI to upload an image to the PiInk via a file upload or an image link.
**If you ever are unable to access the WebUI, press the `A` button on the back of the PiInk and an info screen will pop up.**

### Uploading an image via cURL
Images can be uploaded to the frame over the command line by using cURL.

Here is an example command: `curl -X POST -F file=@image.png piink.local`

### Settings
In the PiInk Settings, set options for the PiInk such as orientation or automatic image adjustment. Reboot or shut down PiInk from the power button in the top right.

There is a button labeled `Clear Ghosting` that can be pressed to cause the display to "scrub" the image to fix image ghosting issues.

### PiInk Buttons
Located on the backside of the PiInk's display are four buttons: A, B, C, and D. Each of these buttons is designed to execute a specific operation on the PiInk. Refer to the table below for the function associated with each button:
| Button | Function |
| :---: |:---|
| `A` | Display the PiInk info screen |
| `B` | Rotate the current image clockwise |
| `C` | Rotate the current image counterclockwise |
| `D` | Reboot the PiInk |


# Parts List

PiInk's 3D printed mount is tailored to fit the Raspberry Pi Zero family, but it's versatile enough to be used with any Raspberry Pi model. Here's what you'll need to build your own PiInk:

- **Raspberry Pi**: Purchase a Pi Zero or other Raspberry Pi model from websites like [Adafruit](https://www.adafruit.com/category/105) or [Pimoroni](https://shop.pimoroni.com/collections/raspberry-pi).
- **E-Ink Display**: Specific details are in the next section.
- **3D-Printed Stand**: Required for mounting the E-Ink Display.

### E-Ink Display


**PiInk uses a Pimoroni Inky Impression E-Ink Display, available in 3 sizes: 4", 5.7", & 7.3" You can purchase one at the links below.**
###### Note: The larger the display, the longer it takes to refresh an image.
- **[4 Inch Display](https://shop.pimoroni.com/products/inky-impression-4)**
- **[5.7 Inch Display](https://shop.pimoroni.com/products/inky-impression-5-7)**
- **[7.3 Inch Display](https://shop.pimoroni.com/products/inky-impression-7-3)**

The included mounting hardware is used to secure the Inky Impression to the 3D-printed stand.


# Issues & Suggestions
If you encounter any issues or have any suggestions, please submit them through the [GitHub Issues](https://github.com/tlstommy/piink/issues) page. Your feedback is greatly appreciated!




