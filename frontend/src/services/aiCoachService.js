// aiCoachService.js
import axios from 'axios';

const API_URL = 'http://localhost:8000';

// Create axios instance with auth header
const getAuthHeader = () => {
  const user = JSON.parse(localStorage.getItem('user'));
  return user?.access_token ? { Authorization: `Bearer ${user.access_token}` } : {};
};

// AI Coach service
const aiCoachService = {
  // Ask a question to the AI Coach
  askQuestion: async (question, conversationId = null) => {
    try {
      const response = await axios.post(
        `${API_URL}/ai-coach/ask`,
        { question, conversation_id: conversationId },
        { headers: getAuthHeader() }
      );
      return response.data;
    } catch (error) {
      console.error('Error asking AI Coach:', error);
      throw error;
    }
  }
};

export default aiCoachService;