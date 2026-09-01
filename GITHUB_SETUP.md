# Publishing Yakushi Control Deck to GitHub

The public repository is:

```text
https://github.com/KayamiYakushi/yakushi-control-deck
```

## Normal release workflow

Before publishing a release, run the non-destructive package check:

```bash
./smoke-test.sh
```

Then commit the prepared release on `main`, push it, create an annotated version tag, and push the tag. Replace `<version>` with the release version, for example `v1.2.1`:

```bash
git switch main
git pull --ff-only origin main
git add -A
git commit -m "Release <version>"
git push origin main
git tag -a <version> -m "Yakushi Control Deck <version>"
git push origin <version>
```

Create a GitHub Release from that existing tag and attach the matching `.tar.gz` and `.zip` archives.

## Fresh-user install

```bash
git clone https://github.com/KayamiYakushi/yakushi-control-deck.git
cd yakushi-control-deck
./smoke-test.sh
./install.sh
./doctor.sh
```

Fish users may use `./install.fish` instead of `./install.sh`.
