wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

dpkg -i google-chrome-stable_current_amd64.deb

apt --fix-broken install -y

chrome_version=$(google-chrome-stable --version)

chromedriver_version=$(curl "https://chromedriver.storage.googleapis.com/LATEST_RELEASE")

curl -Lo chromedriver_linux64.zip "https://chromedriver.storage.googleapis.com/${chromedriver_version}/chromedriver_linux64.zip"

mkdir -p "chromedriver/stable"
unzip -q "chromedriver_linux64.zip" -d "chromedriver/stable"
chmod +x "chromedriver/stable/chromedriver"