import QtQuick 2.15
import QtQuick.Controls 2.15 as QQC2
import QtQuick.Layouts 1.15
import QtQuick.Effects
import SddmComponents 2.0

Item {
    id: root
    width: 1920
    height: 1080
    focus: true

    property int sessionIndex: sessionBox.currentIndex
    property color accentColor: config.accent || "#e8a29a"
    property color backgroundColor: config.backgroundColor || "#1a1414"
    property color surfaceColor: config.surface || "#181313"
    property color surfaceAltColor: config.surfaceAlt || "#241c1c"
    property color foregroundColor: config.foreground || "#e8a29a"
    property color mutedColor: config.muted || "#8e7370"
    property color borderColor: config.border || "#3f292a"
    property string fontFamily: config.font || "serif"
    property bool clock24: String(config.clock24).toLowerCase() !== "false"
    property bool showDate: String(config.showDate).toLowerCase() !== "false"
    property real blurStrength: Math.max(0.0, Math.min(1.0, Number(config.blurStrength || 0.55)))
    property real dimOpacity: Math.max(0.0, Math.min(0.85, Number(config.dimOpacity || 0.30)))
    property string statusText: ""
    property bool authenticating: false
    property bool previewMode: String(config.previewMode).toLowerCase() === "true"
    property string currentUser: {
        var remembered = String(userModel.lastUser || "").trim()
        if (remembered.length > 0)
            return remembered
        return String(config.defaultUser || "").trim()
    }

    function submitLogin() {
        if (authenticating || currentUser.length === 0)
            return

        if (previewMode) {
            statusText = "PREVIEW MODE // LOGIN DISABLED"
            previewMessageTimer.restart()
            passwordField.forceActiveFocus()
            return
        }

        authenticating = true
        statusText = "AUTHENTICATING"
        sddm.login(currentUser, passwordField.text, sessionIndex)
    }

    function updateClock() {
        var now = new Date()
        clockText.text = Qt.formatTime(now, clock24 ? "HH:mm" : "h:mm AP")
        dateText.text = Qt.formatDate(now, "dddd, dd MMMM")
    }

    Connections {
        target: sddm
        function onLoginSucceeded() {
            root.statusText = "WELCOME"
        }
        function onLoginFailed() {
            root.authenticating = false
            root.statusText = "AUTHENTICATION FAILED"
            passwordField.text = ""
            passwordField.forceActiveFocus()
            failureAnimation.restart()
        }
        function onInformationMessage(message) {
            root.statusText = message
        }
    }

    Timer {
        id: previewMessageTimer
        interval: 1800
        repeat: false
        onTriggered: {
            if (root.previewMode)
                root.statusText = ""
        }
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: root.updateClock()
    }

    Rectangle {
        anchors.fill: parent
        color: root.backgroundColor
    }

    Image {
        id: wallpaper
        anchors.fill: parent
        source: config.background ? Qt.resolvedUrl(config.background) : ""
        fillMode: Image.PreserveAspectCrop
        visible: true
        asynchronous: true
        cache: true
    }

    MultiEffect {
        anchors.fill: parent
        source: wallpaper
        visible: wallpaper.status === Image.Ready
        blurEnabled: root.blurStrength > 0.01
        blur: root.blurStrength
        blurMax: 48
        autoPaddingEnabled: false
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: root.dimOpacity
    }

    Rectangle {
        anchors.fill: parent
        color: root.backgroundColor
        opacity: wallpaper.status === Image.Ready ? 0.10 : 0.52
    }

    // Small technical header mirrors the Yakushi Control Deck visual language.
    Row {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: 34
        anchors.topMargin: 26
        spacing: 12

        Text {
            text: "薬"
            color: root.accentColor
            font.pixelSize: 27
            font.bold: true
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: "YAKUSHI // LOGIN"
            color: root.mutedColor
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 12
            font.letterSpacing: 1.8
        }
    }

    Column {
        id: centerStack
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: -16
        width: Math.min(470, parent.width * 0.76)
        spacing: 14

        Text {
            id: clockText
            anchors.horizontalCenter: parent.horizontalCenter
            text: "00:00"
            color: root.foregroundColor
            font.family: root.fontFamily
            font.pixelSize: Math.min(92, root.width * 0.052)
            font.weight: Font.DemiBold
        }

        Text {
            id: dateText
            anchors.horizontalCenter: parent.horizontalCenter
            visible: root.showDate
            color: root.mutedColor
            font.family: root.fontFamily
            font.pixelSize: 18
        }

        Item { width: 1; height: 18 }

        Rectangle {
            id: loginCard
            width: parent.width
            height: formColumn.implicitHeight + 42
            color: Qt.rgba(root.surfaceColor.r, root.surfaceColor.g, root.surfaceColor.b, 0.90)
            border.color: root.borderColor
            border.width: 1
            radius: 16

            SequentialAnimation {
                id: failureAnimation
                NumberAnimation { target: loginCard; property: "x"; to: -8; duration: 55 }
                NumberAnimation { target: loginCard; property: "x"; to: 8; duration: 70 }
                NumberAnimation { target: loginCard; property: "x"; to: -5; duration: 55 }
                NumberAnimation { target: loginCard; property: "x"; to: 0; duration: 55 }
            }

            Column {
                id: formColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 21
                spacing: 12

                Text {
                    text: "SESSION AUTHENTICATION"
                    color: root.mutedColor
                    font.family: "JetBrainsMono Nerd Font"
                    font.pixelSize: 10
                    font.letterSpacing: 1.6
                }

                Rectangle {
                    width: parent.width
                    height: 44
                    color: Qt.rgba(root.surfaceAltColor.r, root.surfaceAltColor.g, root.surfaceAltColor.b, 0.72)
                    border.color: root.borderColor
                    border.width: 1
                    radius: 12

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 15
                        anchors.rightMargin: 15
                        spacing: 12

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "USER"
                            color: root.mutedColor
                            font.family: "JetBrainsMono Nerd Font"
                            font.pixelSize: 9
                            font.letterSpacing: 1.4
                        }

                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 1
                            height: 16
                            color: root.borderColor
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.currentUser.length > 0 ? root.currentUser : "NO USER"
                            color: root.foregroundColor
                            font.family: "JetBrainsMono Nerd Font"
                            font.pixelSize: 13
                            elide: Text.ElideRight
                        }
                    }
                }

                QQC2.TextField {
                    id: passwordField
                    width: parent.width
                    height: 54
                    placeholderText: "Enter password"
                    echoMode: TextInput.Password
                    passwordCharacter: "•"
                    color: root.foregroundColor
                    placeholderTextColor: root.mutedColor
                    selectionColor: root.accentColor
                    selectedTextColor: root.backgroundColor
                    font.family: "JetBrainsMono Nerd Font"
                    font.pixelSize: 15
                    leftPadding: 16
                    rightPadding: 16
                    background: Rectangle {
                        color: root.surfaceAltColor
                        border.color: passwordField.activeFocus ? root.accentColor : root.borderColor
                        border.width: passwordField.activeFocus ? 2 : 1
                        radius: 12
                    }
                    Keys.onReturnPressed: root.submitLogin()
                    Keys.onEnterPressed: root.submitLogin()
                }

                RowLayout {
                    width: parent.width
                    spacing: 10

                    QQC2.ComboBox {
                        id: sessionBox
                        Layout.fillWidth: true
                        Layout.preferredHeight: 42
                        model: sessionModel
                        textRole: "name"
                        currentIndex: sessionModel.lastIndex >= 0 ? sessionModel.lastIndex : 0
                        font.family: "JetBrainsMono Nerd Font"
                        font.pixelSize: 11
                        contentItem: Text {
                            leftPadding: 12
                            rightPadding: 28
                            text: sessionBox.displayText
                            color: root.mutedColor
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                            font: sessionBox.font
                        }
                        background: Rectangle {
                            color: root.surfaceAltColor
                            border.color: sessionBox.activeFocus ? root.accentColor : root.borderColor
                            radius: 10
                        }
                    }

                    QQC2.Button {
                        id: loginButton
                        Layout.preferredWidth: 132
                        Layout.preferredHeight: 42
                        enabled: !root.authenticating && root.currentUser.length > 0
                        text: root.authenticating ? "WAIT" : "LOGIN"
                        contentItem: Text {
                            text: loginButton.text
                            color: root.backgroundColor
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.family: "JetBrainsMono Nerd Font"
                            font.pixelSize: 11
                            font.bold: true
                            font.letterSpacing: 1.4
                        }
                        background: Rectangle {
                            color: loginButton.down ? root.foregroundColor : root.accentColor
                            opacity: loginButton.enabled ? 1.0 : 0.55
                            radius: 10
                        }
                        onClicked: root.submitLogin()
                    }
                }

                Text {
                    width: parent.width
                    text: root.statusText
                    visible: text.length > 0
                    color: root.statusText === "AUTHENTICATION FAILED" ? "#dc4650" : root.mutedColor
                    horizontalAlignment: Text.AlignHCenter
                    font.family: "JetBrainsMono Nerd Font"
                    font.pixelSize: 10
                    font.letterSpacing: 1.2
                }
            }
        }
    }

    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
        spacing: 9

        QQC2.Button {
            visible: sddm.canReboot
            text: "REBOOT"
            onClicked: sddm.reboot()
            contentItem: Text {
                text: parent.text
                color: root.mutedColor
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.family: "JetBrainsMono Nerd Font"
                font.pixelSize: 10
                font.letterSpacing: 1.2
            }
            background: Rectangle {
                implicitWidth: 92
                implicitHeight: 34
                color: parent.hovered ? root.surfaceAltColor : "transparent"
                border.color: root.borderColor
                radius: 8
            }
        }

        QQC2.Button {
            visible: sddm.canPowerOff
            text: "POWER OFF"
            onClicked: sddm.powerOff()
            contentItem: Text {
                text: parent.text
                color: root.mutedColor
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.family: "JetBrainsMono Nerd Font"
                font.pixelSize: 10
                font.letterSpacing: 1.2
            }
            background: Rectangle {
                implicitWidth: 108
                implicitHeight: 34
                color: parent.hovered ? root.surfaceAltColor : "transparent"
                border.color: root.borderColor
                radius: 8
            }
        }
    }

    Component.onCompleted: {
        root.updateClock()
        passwordField.forceActiveFocus()
        if (root.currentUser.length === 0)
            root.statusText = "NO LOGIN USER AVAILABLE"
    }
}
