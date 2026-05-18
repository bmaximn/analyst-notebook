const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const fs = require('fs')

const isDev = process.env.ELECTRON_DEV === 'true'

function createWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    titleBarStyle: 'hiddenInset',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  if (isDev) {
    win.loadURL('http://localhost:5173')
    win.webContents.openDevTools()
  } else {
    win.loadFile(path.join(__dirname, '../dist/index.html'))
  }
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

// Де зберігаємо проекти — у папці даних програми (не в /tmp)
const dataDir = path.join(app.getPath('userData'), 'projects')

ipcMain.handle('save-project', async (_event, { name, data }) => {
  if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir, { recursive: true })
  const filePath = path.join(dataDir, `${name}.json`)
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8')
  return { success: true }
})

ipcMain.handle('load-project', async (_event, { name }) => {
  const filePath = path.join(dataDir, `${name}.json`)
  if (!fs.existsSync(filePath)) return null
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'))
})

ipcMain.handle('list-projects', async () => {
  if (!fs.existsSync(dataDir)) return []
  return fs.readdirSync(dataDir)
    .filter(f => f.endsWith('.json'))
    .map(f => f.replace('.json', ''))
})
