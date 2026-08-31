# Publishing Yakushi Control Deck to GitHub

1. On GitHub, create a new **Public** repository named `yakushi-control-deck`.
2. Do not initialize it with a README, `.gitignore`, or license; this project already contains them.
3. In the extracted project directory, run:

```fish
git init -b main
git add .
git commit -m "Release Yakushi Control Deck v1.0.0"
git remote add origin https://github.com/KayamiYakushi/yakushi-control-deck.git
git push -u origin main
git tag -a v1.0.0 -m "Yakushi Control Deck v1.0.0"
git push origin v1.0.0
```

After the push, GitHub users can install with:

```bash
git clone https://github.com/KayamiYakushi/yakushi-control-deck.git
cd yakushi-control-deck
./install.sh
```
