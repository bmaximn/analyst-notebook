const { contextBridge, ipcRenderer } = require('electron')

// contextBridge — це "міст" між Electron і React.
// Він дозволяє React викликати функції Node.js безпечно,
// без прямого доступу до системи (contextIsolation: true).
contextBridge.exposeInMainWorld('api', {
  saveProject: (name, data) => ipcRenderer.invoke('save-project', { name, data }),
  loadProject: (name) => ipcRenderer.invoke('load-project', { name }),
  listProjects: () => ipcRenderer.invoke('list-projects')
})
