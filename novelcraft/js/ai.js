/**
 * OpenAI Chat API 封装模块
 * 支持多模型切换，统一 error 处理，流式/非流式可选
 * 配置由外部传入（按项目隔离）
 */

export class AIModule {
  /**
   * 发送聊天请求（非流式）
   * @param {Array<{role:string, content:string}>} messages
   * @param {Object} config - { apiKey, baseURL, model }
   * @param {Object} options - temperature 等
   * @returns {Promise<string>}  assistant 的回复内容
   */
  async chat(messages, config, options = {}) {
    if (!config?.apiKey) {
      throw new Error('请先配置 API Key');
    }

    const baseURL = (config.baseURL || 'https://api.openai.com/v1').replace(/\/$/, '');
    const model = config.model || 'gpt-4o';

    const payload = {
      model,
      messages,
      temperature: options.temperature ?? 0.7,
      ...(options.response_format ? { response_format: options.response_format } : {}),
    };

    const res = await fetch(`${baseURL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.apiKey}`,
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      let errText = `HTTP ${res.status}`;
      try {
        const errData = await res.json();
        errText = errData.error?.message || JSON.stringify(errData);
      } catch {
        errText = await res.text() || errText;
      }
      throw new Error(errText);
    }

    const data = await res.json();
    return data.choices?.[0]?.message?.content || '';
  }

  /**
   * 流式聊天请求
   * @param {Array<{role:string, content:string}>} messages
   * @param {Object} config - { apiKey, baseURL, model }
   * @param {Function} onChunk - (text: string, isDone: boolean) => void
   * @param {Object} options
   */
  async chatStream(messages, config, onChunk, options = {}) {
    if (!config?.apiKey) {
      throw new Error('请先配置 API Key');
    }

    const baseURL = (config.baseURL || 'https://api.openai.com/v1').replace(/\/$/, '');
    const model = config.model || 'gpt-4o';

    const payload = {
      model,
      messages,
      temperature: options.temperature ?? 0.7,
      stream: true,
      ...(options.response_format ? { response_format: options.response_format } : {}),
    };

    const res = await fetch(`${baseURL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.apiKey}`,
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      let errText = `HTTP ${res.status}`;
      try {
        const errData = await res.json();
        errText = errData.error?.message || JSON.stringify(errData);
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
        if (!trimmed || trimmed === 'data: [DONE]') continue;
        if (trimmed.startsWith('data: ')) {
          try {
            const json = JSON.parse(trimmed.slice(6));
            const delta = json.choices?.[0]?.delta?.content || '';
            if (delta) onChunk(delta, false);
          } catch {
            // ignore malformed SSE
          }
        }
      }
    }

    onChunk('', true);
  }
}

export const ai = new AIModule();
