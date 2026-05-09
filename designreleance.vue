<script setup lang="ts">
import { ref, onMounted } from 'vue'

/*
  Reactive state
*/
const devices = ref<any[]>([])
const scenes = ref<any>({})
const sceneNames = ['happy', 'focus', 'party']

/*
  Fetch lights + scenes on page load
*/
onMounted(async () => {
  try {
    // Fetch connected lights
    const lights = await $fetch('http://localhost:8000/lights')
    devices.value = lights

    // Fetch saved scenes
    const sceneData = await $fetch('http://localhost:8000/api/scenes')
    scenes.value = sceneData

    // Ensure structure exists
    sceneNames.forEach(scene => {
      if (!scenes.value[scene]) {
        scenes.value[scene] = {
          lights: {},
          playlist: ""
        }
      }

      devices.value.forEach(device => {
        if (!scenes.value[scene].lights[device.device]) {
          scenes.value[scene].lights[device.device] = "#ffffff"
        }
      })
    })

  } catch (err) {
    console.error("Error loading data:", err)
  }
})

/*
  Save Scene
*/
async function saveScene(scene: string) {
  try {
    await $fetch('http://localhost:8000/api/scenes', {
      method: 'POST',
      body: {
        name: scene,
        colors: scenes.value[scene].lights,
        playlist: scenes.value[scene].playlist
      }
    })

    alert("Scene saved!")
  } catch (err) {
    console.error(err)
    alert("Error saving scene")
  }
}

/*
  Trigger Scene
*/
async function triggerScene(scene: string) {
  try {
    await $fetch(`http://localhost:8000/api/trigger/${scene}`)
    alert("Scene triggered!")
  } catch (err) {
    console.error(err)
    alert("Error triggering scene")
  }
}

/*
  Logout
*/
function logout() {
  window.location.href = "http://localhost:8000/logout"
}
</script>

<template>
  <div>
    <!-- Header -->
    <header>
      <h1>Smart Lighting Scene Controller</h1>
      <button class="logout-button" @click="logout">
        Logout
      </button>
    </header>

    <!-- Lights Section -->
    <section>
      <h2>Connected Lights</h2>
      <ul>
        <li v-for="device in devices" :key="device.device">
          {{ device.name }} ({{ device.device }})
        </li>
      </ul>
    </section>

    <!-- Scenes Section -->
    <section>
      <h2>Customize Scenes</h2>

      <div
        v-for="scene in sceneNames"
        :key="scene"
        class="scene"
      >
        <h3>{{ scene }}</h3>

        <!-- Color Pickers -->
        <div>
          <input
            v-for="device in devices"
            :key="device.device"
            type="color"
            v-model="scenes[scene].lights[device.device]"
          />
        </div>

        <!-- Spotify Playlist -->
        <label>Enter Spotify playlist link:</label>
        <input
          type="text"
          v-model="scenes[scene].playlist"
          required
        />

        <br /><br />

        <!-- Buttons -->
        <button @click="saveScene(scene)">
          Save
        </button>

        <button @click="triggerScene(scene)">
          Trigger
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.scene {
  margin-bottom: 2rem;
}

.logout-button {
  padding: 6px 12px;
}
</style>