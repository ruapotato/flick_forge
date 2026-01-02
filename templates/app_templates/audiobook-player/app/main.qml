// Flick Audiobook Player
// AGPL-3.0 License
// AI-generated with human oversight

import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtMultimedia 5.15
import Qt.labs.folderlistmodel 2.15

Window {
    id: root
    visible: true
    width: 1080
    height: 2400
    title: "Audiobook Player"
    color: "#0a0a0f"

    // Theme colors
    property color accentColor: "#6366f1"
    property color surfaceColor: "#1a1a2e"
    property color textPrimary: "#ffffff"
    property color textSecondary: "#9ca3af"
    property color borderColor: "#2d2d3d"

    // Player state
    property string currentFile: ""
    property string currentTitle: "No audiobook selected"
    property real playbackSpeed: 1.0
    property int sleepTimerMinutes: 0
    property var bookmarks: []

    // Media player
    MediaPlayer {
        id: audioPlayer
        source: currentFile
        onPositionChanged: progressSlider.value = position
        onDurationChanged: progressSlider.to = duration
        onStatusChanged: {
            if (status === MediaPlayer.EndOfMedia) {
                playNextChapter()
            }
        }
    }

    // Sleep timer
    Timer {
        id: sleepTimer
        interval: sleepTimerMinutes * 60 * 1000
        running: sleepTimerMinutes > 0 && audioPlayer.playbackState === MediaPlayer.PlayingState
        onTriggered: {
            audioPlayer.pause()
            sleepTimerMinutes = 0
            showToast("Sleep timer: Paused playback")
        }
    }

    // Audiobook folder model
    FolderListModel {
        id: audiobookModel
        folder: "file:///home/droidian/Audiobooks"
        nameFilters: ["*.mp3", "*.m4a", "*.m4b", "*.ogg", "*.opus", "*.flac"]
        showDirs: true
        showFiles: true
        sortField: FolderListModel.Name
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 24

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: 16

            Text {
                text: "Audiobook Player"
                font.pixelSize: 28
                font.bold: true
                color: textPrimary
            }

            Item { Layout.fillWidth: true }

            // Speed control button
            Rectangle {
                width: 80
                height: 40
                radius: 20
                color: surfaceColor
                border.color: borderColor

                Text {
                    anchors.centerIn: parent
                    text: playbackSpeed.toFixed(1) + "x"
                    color: textPrimary
                    font.pixelSize: 16
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: speedMenu.open()
                }
            }

            // Sleep timer button
            Rectangle {
                width: 48
                height: 48
                radius: 24
                color: sleepTimerMinutes > 0 ? accentColor : surfaceColor
                border.color: borderColor

                Text {
                    anchors.centerIn: parent
                    text: sleepTimerMinutes > 0 ? sleepTimerMinutes + "m" : "ZZ"
                    color: textPrimary
                    font.pixelSize: 14
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: sleepMenu.open()
                }
            }
        }

        // Now playing card
        Rectangle {
            Layout.fillWidth: true
            height: 200
            radius: 16
            color: surfaceColor
            border.color: borderColor

            RowLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 20

                // Album art placeholder
                Rectangle {
                    width: 160
                    height: 160
                    radius: 12
                    color: accentColor

                    Text {
                        anchors.centerIn: parent
                        text: currentTitle.charAt(0).toUpperCase()
                        font.pixelSize: 64
                        font.bold: true
                        color: "white"
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 8

                    Text {
                        Layout.fillWidth: true
                        text: currentTitle
                        font.pixelSize: 22
                        font.bold: true
                        color: textPrimary
                        elide: Text.ElideRight
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                    }

                    Text {
                        text: formatTime(audioPlayer.position) + " / " + formatTime(audioPlayer.duration)
                        font.pixelSize: 16
                        color: textSecondary
                    }

                    Item { Layout.fillHeight: true }

                    // Playback controls
                    RowLayout {
                        spacing: 16

                        // Rewind 30s
                        Rectangle {
                            width: 56
                            height: 56
                            radius: 28
                            color: borderColor

                            Text {
                                anchors.centerIn: parent
                                text: "-30"
                                color: textPrimary
                                font.pixelSize: 16
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: audioPlayer.seek(Math.max(0, audioPlayer.position - 30000))
                            }
                        }

                        // Play/Pause
                        Rectangle {
                            width: 72
                            height: 72
                            radius: 36
                            color: accentColor

                            Text {
                                anchors.centerIn: parent
                                text: audioPlayer.playbackState === MediaPlayer.PlayingState ? "II" : ">"
                                color: "white"
                                font.pixelSize: 28
                                font.bold: true
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    if (audioPlayer.playbackState === MediaPlayer.PlayingState) {
                                        audioPlayer.pause()
                                    } else {
                                        audioPlayer.play()
                                    }
                                }
                            }
                        }

                        // Forward 30s
                        Rectangle {
                            width: 56
                            height: 56
                            radius: 28
                            color: borderColor

                            Text {
                                anchors.centerIn: parent
                                text: "+30"
                                color: textPrimary
                                font.pixelSize: 16
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: audioPlayer.seek(Math.min(audioPlayer.duration, audioPlayer.position + 30000))
                            }
                        }

                        // Bookmark
                        Rectangle {
                            width: 56
                            height: 56
                            radius: 28
                            color: borderColor

                            Text {
                                anchors.centerIn: parent
                                text: "BM"
                                color: textPrimary
                                font.pixelSize: 14
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: addBookmark()
                            }
                        }
                    }
                }
            }
        }

        // Progress slider
        Slider {
            id: progressSlider
            Layout.fillWidth: true
            from: 0
            to: audioPlayer.duration
            value: audioPlayer.position

            background: Rectangle {
                x: progressSlider.leftPadding
                y: progressSlider.topPadding + progressSlider.availableHeight / 2 - height / 2
                implicitWidth: 200
                implicitHeight: 8
                width: progressSlider.availableWidth
                height: implicitHeight
                radius: 4
                color: borderColor

                Rectangle {
                    width: progressSlider.visualPosition * parent.width
                    height: parent.height
                    color: accentColor
                    radius: 4
                }
            }

            handle: Rectangle {
                x: progressSlider.leftPadding + progressSlider.visualPosition * (progressSlider.availableWidth - width)
                y: progressSlider.topPadding + progressSlider.availableHeight / 2 - height / 2
                implicitWidth: 24
                implicitHeight: 24
                radius: 12
                color: progressSlider.pressed ? Qt.lighter(accentColor) : accentColor
            }

            onMoved: audioPlayer.seek(value)
        }

        // Library section
        Text {
            text: "Your Library"
            font.pixelSize: 20
            font.bold: true
            color: textPrimary
        }

        // File list
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: audiobookModel
            clip: true
            spacing: 8

            delegate: Rectangle {
                width: parent ? parent.width : 0
                height: 72
                radius: 12
                color: currentFile === fileUrl ? Qt.darker(accentColor, 1.5) : surfaceColor
                border.color: borderColor

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 16

                    Rectangle {
                        width: 40
                        height: 40
                        radius: 8
                        color: fileIsDir ? "#22d3ee" : accentColor

                        Text {
                            anchors.centerIn: parent
                            text: fileIsDir ? "D" : "A"
                            color: "white"
                            font.pixelSize: 18
                            font.bold: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Text {
                            Layout.fillWidth: true
                            text: fileName
                            font.pixelSize: 16
                            color: textPrimary
                            elide: Text.ElideRight
                        }

                        Text {
                            text: fileIsDir ? "Folder" : "Audiobook"
                            font.pixelSize: 14
                            color: textSecondary
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (fileIsDir) {
                            audiobookModel.folder = fileUrl
                        } else {
                            currentFile = fileUrl
                            currentTitle = fileName.replace(/\.[^/.]+$/, "")
                            audioPlayer.play()
                        }
                    }
                }
            }

            Text {
                anchors.centerIn: parent
                visible: audiobookModel.count === 0
                text: "No audiobooks found.\nAdd files to ~/Audiobooks"
                font.pixelSize: 18
                color: textSecondary
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    // Speed menu
    Popup {
        id: speedMenu
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        width: 300
        height: 400
        modal: true

        background: Rectangle {
            color: surfaceColor
            radius: 16
            border.color: borderColor
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            Text {
                text: "Playback Speed"
                font.pixelSize: 20
                font.bold: true
                color: textPrimary
            }

            Repeater {
                model: [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]

                Rectangle {
                    Layout.fillWidth: true
                    height: 48
                    radius: 8
                    color: playbackSpeed === modelData ? accentColor : borderColor

                    Text {
                        anchors.centerIn: parent
                        text: modelData.toFixed(2) + "x"
                        color: textPrimary
                        font.pixelSize: 18
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            playbackSpeed = modelData
                            audioPlayer.playbackRate = modelData
                            speedMenu.close()
                        }
                    }
                }
            }
        }
    }

    // Sleep timer menu
    Popup {
        id: sleepMenu
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        width: 300
        height: 350
        modal: true

        background: Rectangle {
            color: surfaceColor
            radius: 16
            border.color: borderColor
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            Text {
                text: "Sleep Timer"
                font.pixelSize: 20
                font.bold: true
                color: textPrimary
            }

            Repeater {
                model: [0, 15, 30, 45, 60, 90]

                Rectangle {
                    Layout.fillWidth: true
                    height: 48
                    radius: 8
                    color: sleepTimerMinutes === modelData ? accentColor : borderColor

                    Text {
                        anchors.centerIn: parent
                        text: modelData === 0 ? "Off" : modelData + " minutes"
                        color: textPrimary
                        font.pixelSize: 18
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            sleepTimerMinutes = modelData
                            sleepMenu.close()
                            if (modelData > 0) {
                                showToast("Sleep timer set for " + modelData + " minutes")
                            }
                        }
                    }
                }
            }
        }
    }

    // Toast notification
    Rectangle {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 100
        width: toastText.width + 40
        height: 48
        radius: 24
        color: surfaceColor
        border.color: borderColor
        opacity: 0
        visible: opacity > 0

        Text {
            id: toastText
            anchors.centerIn: parent
            color: textPrimary
            font.pixelSize: 16
        }

        Behavior on opacity {
            NumberAnimation { duration: 200 }
        }
    }

    Timer {
        id: toastTimer
        interval: 2000
        onTriggered: toast.opacity = 0
    }

    function showToast(message) {
        toastText.text = message
        toast.opacity = 1
        toastTimer.restart()
    }

    function formatTime(ms) {
        var seconds = Math.floor(ms / 1000)
        var minutes = Math.floor(seconds / 60)
        var hours = Math.floor(minutes / 60)
        seconds = seconds % 60
        minutes = minutes % 60

        if (hours > 0) {
            return hours + ":" + pad(minutes) + ":" + pad(seconds)
        }
        return minutes + ":" + pad(seconds)
    }

    function pad(n) {
        return n < 10 ? "0" + n : n
    }

    function addBookmark() {
        var bookmark = {
            position: audioPlayer.position,
            title: currentTitle,
            timestamp: new Date().toISOString()
        }
        bookmarks.push(bookmark)
        showToast("Bookmark added at " + formatTime(audioPlayer.position))
    }

    function playNextChapter() {
        // Find next file in folder
        for (var i = 0; i < audiobookModel.count; i++) {
            if (audiobookModel.get(i, "fileUrl") === currentFile) {
                if (i + 1 < audiobookModel.count && !audiobookModel.get(i + 1, "fileIsDir")) {
                    currentFile = audiobookModel.get(i + 1, "fileUrl")
                    currentTitle = audiobookModel.get(i + 1, "fileName").replace(/\.[^/.]+$/, "")
                    audioPlayer.play()
                }
                break
            }
        }
    }
}
