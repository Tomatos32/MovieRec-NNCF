<template>
  <!-- 1. Background Gradient -->
  <div class="flex min-h-screen bg-gradient-to-br from-[#020024] via-[#090979] to-[#00d4ff] items-center justify-center p-4">
    <div class="flex w-full max-w-5xl rounded-3xl shadow-2xl overflow-hidden h-[600px] border border-white/10 backdrop-blur-sm">
      
      <!-- Left Side: Branding & Vector Image Placeholder -->
      <!-- Kept strictly for the vector image, solid or semi-transparent based on user vector -->
      <div class="hidden md:flex w-1/2 bg-[#0052D4]/80 relative items-center justify-center overflow-hidden backdrop-blur-md">
         <img src="@/assets/loginpage.svg" alt="Login Visual" class="w-full h-full object-cover opacity-90 hover:scale-105 transition-transform duration-700" />
      </div>

      <!-- Right Side: Login Form (Glassmorphism) -->
      <div class="w-full md:w-1/2 p-12 flex flex-col justify-center bg-white/10 backdrop-blur-xl relative z-10">
        <div class="max-w-xs mx-auto w-full">
          <div class="mb-10">
            <h2 class="text-2xl font-bold text-white mb-2">Hello Again!</h2>
            <p class="text-gray-300">Welcome Back</p>
          </div>

          <form @submit.prevent="handleLogin" class="space-y-5">
            <div>
               <!-- Email/Username Input -->
              <div class="relative">
                <input 
                  v-model="form.username" 
                  type="text" 
                  class="w-full bg-white/5 border border-white/10 rounded-full px-5 py-3 pl-10 text-sm text-white outline-none focus:border-blue-400 focus:bg-white/10 transition-all placeholder-gray-400"
                  placeholder="Email Address"
                  required
                >
                <Mail class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
              </div>
            </div>

            <div>
              <!-- Password Input -->
              <div class="relative">
                <input 
                  v-model="form.password" 
                  type="password" 
                  class="w-full bg-white/5 border border-white/10 rounded-full px-5 py-3 pl-10 text-sm text-white outline-none focus:border-blue-400 focus:bg-white/10 transition-all placeholder-gray-400"
                  placeholder="Password"
                  required
                >
                 <Lock class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
              </div>
            </div>

            <button 
              type="submit" 
              class="w-full py-3 bg-[#0052D4] hover:bg-[#0041a8] text-white font-bold rounded-full shadow-[0_4px_14px_0_rgba(0,82,212,0.39)] hover:shadow-[0_6px_20px_rgba(0,82,212,0.23)] transition-all transform hover:-translate-y-0.5 text-sm active:scale-95"
              :disabled="loading"
            >
              <span v-if="loading" class="flex items-center justify-center"><Loader2 class="animate-spin mr-2 w-4 h-4" />Login...</span>
              <span v-else>Login</span>
            </button>
            
            <div class="text-center mt-4">
                 <a href="#" class="text-xs text-blue-200 hover:text-white transition-colors">Forgot Password</a>
            </div>
          </form>

        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/stores/user';
import { ElMessage } from 'element-plus';
import { Mail, Lock, Loader2 } from 'lucide-vue-next';

const router = useRouter();
const userStore = useUserStore();

const form = ref({
  username: '', 
  password: ''
});

const loading = ref(false);

const handleLogin = async () => {
  loading.value = true;
  try {
    await userStore.login(form.value);
    ElMessage.success('Login Successful');
    router.push('/');
  } catch (error: any) {
    console.error('Login error details:', error);
    ElMessage.error(error.message || 'Login Failed');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
/* Add any specific fonts if needed, e.g. Poppins */
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

div {
  font-family: 'Poppins', sans-serif;
}
</style>
