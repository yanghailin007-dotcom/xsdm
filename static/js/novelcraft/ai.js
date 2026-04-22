/**
 * NovelCraft AI 模块
 * 通过后端代理调用标准对话 API
 * 支持系统预设模型和用户自定义模型
 */

export class AIModule {
  /**
   * 发送聊天请求（非流式）
   * @param {Array<{role:string, content:string}>} messages
   * @param {string} modelId - 模型 ID
   * @param {Object} options - temperature 等
   * @returns {Promise<string>} assistant 的回复内容
   */
  async chat(messages, modelId, options = {}) {
    const payload = {
      messages,
      model_id: modelId,
      temperature: options.temperature ?? 0.7,
    };

    const res = await fetch('/api/novelcraft/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      let errText = `HTTP ${res.status}`;
      try {
        const errData = await res.json();
        errText = errData.error || JSON.stringify(errData);
      } catch {
        errText = await res.text() || errText;
      }
      throw new Error(errText);
    }

    const data = await res.json();
    if (!data.success) {
      throw new Error(data.error || '未知错误');
    }
    return data.data?.content || '';
  }

  /**
   * 流式聊天请求
   * @param {Array<{role:string, content:string}>} messages
   * @param {string} modelId - 模型 ID
   * @param {Function} onChunk - (text: string, isDone: boolean) => void
   * @param {Object} options
   */
  async chatStream(messages, modelId, onChunk, options = {}) {
    const payload = {
      messages,
      model_id: modelId,
      temperature: options.temperature ?? 0.7,
    };

    const res = await fetch('/api/novelcraft/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      let errText = `HTTP ${res.status}`;
      try {
        const errData = await res.json();
        errText = errData.error || JSON.stringify(errData);
      } catch {
        errText = await res.text() || errText;
      }
      throw new Error(errText);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed === 'data: [DONE]') {
          if (trimmed === 'data: [DONE]') {
            onChunk('', true);
            return;
          }
          continue;
        }
        if (trimmed.startsWith('data: ')) {
          try {
            const json = JSON.parse(trimmed.slice(6));
            if (json.error) {
              throw new Error(json.error);
            }
            const delta = json.content || '';
            if (delta) onChunk(delta, false);
          } catch (e) {
            if (e.message && !e.message.includes('Unexpected token')) {
              throw e;
            }
          }
        }
      }
    }

    onChunk('', true);
  }

  /**
   * 获取可用模型列表
   */
  async fetchModels() {
    const res = await fetch('/api/novelcraft/models');
    const data = await res.json();
    if (!data.success) {
      throw new Error(data.error || '获取模型列表失败');
    }
    return data.data;
  }

  /**
   * 添加自定义模型
   */
  async addCustomModel(model) {
    const res = await fetch('/api/novelcraft/models', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(model),
    });
    return await res.json();
  }

  /**
   * 删除自定义模型
   */
  async deleteCustomModel(modelId) {
    const res = await fetch(`/api/novelcraft/models/${encodeURIComponent(modelId)}`, {
      method: 'DELETE',
    });
    return await res.json();
  }
}

export const ai = new AIModule();
