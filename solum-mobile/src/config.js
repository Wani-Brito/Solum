// Endereço da API do Solum.
//  - Emulador Android: http://10.0.2.2:8000
//  - Celular com Expo Go: http://IP-DO-SEU-COMPUTADOR:8000  (ex.: http://192.168.0.10:8000)
// Dá para definir sem editar o código:  EXPO_PUBLIC_API_URL=http://192.168.0.10:8000 npx expo start
export const API_URL = (typeof process !== 'undefined' && process.env && process.env.EXPO_PUBLIC_API_URL) || 'http://localhost:8000';
