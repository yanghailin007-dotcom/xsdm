# 角色设计图标注规范

## 目标
在AI生成角色图时，采用 Character Design Sheet 格式，并在图中标注关键特征，确保角色一致性。

## 提示词模板

### 基础结构
```
Character Design Sheet, [角色姓名], 
Layout: Bust-up portrait on left + Full body turnaround on right,
Bust-up: Front view only, chest-up, [面部特征描述],
Full body: Front view (T-pose) + Side view (profile) + Back view,
Front: [正面服装细节],
Side: [侧面特征：发型长度、背包轮廓、身体厚度],
Back: [背面细节：服装后视图、发型背面],
Clean line art, White background, Model sheet style, 7 head proportion, Anime realistic style,
Highly detailed, Sharp focus, 8k --ar 16:9 --niji 6 --style raw
```

### 关键特征标注要求
在图片角落用小字（约占图片高度的3-5%）添加文字标注：

```
右下角标注（角色基础信息）：
- 姓名：XXX
- 年龄：XX岁
- 身高：XXXcm
- 体型：XX

左下角标注（服装特征）：
- 主色调：XXX
- 标志性装饰：XXX
- 特殊标记：XXX（如：左臂红色图腾胎记）

右上角标注（面部特征）：
- 发型：XXX
- 眼睛：XXX
- 表情基调：XXX
```

## 示例（林小满）

### 完整提示词
```
Character Design Sheet, Lin Xiaoman (female delivery rider),
Layout: Bust-up portrait on left + Full body turnaround on right,
Bust-up: Front view only, chest-up, black hair in low ponytail, black frame glasses, determined expression, yellow jacket collar visible,
Full body: Front view (T-pose) + Side view (profile) + Back view,
Front: Yellow tactical delivery jacket with reflective strips, black canvas bag, red Shanhaijing tattoo on left arm visible, holding cracked helmet,
Side: Show ponytail length, bag profile, body thickness,
Back: Show jacket back details, ponytail from behind, tattoo visible on left arm back side,
Text annotation in corners: small text at bottom right corner "林小满·22岁·黄色外卖服·左臂红色图腾胎记", 
Clean line art, White background, Model sheet style, 7 head proportion, Anime realistic style,
Highly detailed, Sharp focus, 8k --ar 16:9 --niji 6 --style raw
```

## 技术实现建议

### 1. 自动生成提示词
修改 `generateCharacterPortraitPrompt` 函数，增加设计图模式：

```javascript
// 新增函数：生成角色设计图提示词
generateCharacterDesignSheetPrompt(character) {
    // 提取角色特征
    const name = character.name;
    const age = character.age || '未知';
    const physicalDesc = character.living_characteristics?.physical_presence || '';
    
    // 构建标注文本
    const annotation = `${name}·${age}岁·${this.extractKeyFeatures(physicalDesc)}`;
    
    // 构建完整提示词
    return `Character Design Sheet, ${name}, ... Text annotation: "${annotation}" ...`;
}
```

### 2. 特征提取规则
自动从角色描述中提取关键特征用于标注：

```javascript
extractKeyFeatures(description) {
    const features = [];
    
    // 颜色提取
    const colorKeywords = ['红色', '黄色', '蓝色', '白色', '黑色', '紫色', '金色'];
    for (const color of colorKeywords) {
        if (description.includes(color)) {
            features.push(color);
            break; // 只取第一个主要颜色
        }
    }
    
    // 特殊标记提取
    const markKeywords = ['胎记', '疤痕', '纹身', '图腾', '印记', '痣'];
    for (const mark of markKeywords) {
        if (description.includes(mark)) {
            const match = description.match(new RegExp(`(.{0,5}${mark}.{0,5})`));
            if (match) features.push(match[0]);
            break;
        }
    }
    
    // 服装类型提取
    const clothingKeywords = ['外卖服', '长袍', '战甲', '西装', '旗袍', '校服'];
    for (const clothing of clothingKeywords) {
        if (description.includes(clothing)) {
            features.push(clothing);
            break;
        }
    }
    
    return features.slice(0, 3).join('·'); // 最多3个特征
}
```

### 3. UI 添加生成选项
在视觉资产库中添加"生成设计图"按钮：

```html
<button id="vaGenerateDesignSheetBtn" title="生成带标注的角色设计图">
    📐 设计图
</button>
```

### 4. 显示优化
生成的设计图在卡片中显示时：
- hover 时放大显示
- 点击可查看完整设计图
- 标注文字可单独复制

## 优势

1. **一致性保障**：AI生成时就被"强制"记住关键特征
2. **易于对比**：设计图格式便于对比不同角度
3. **信息完整**：标注包含最重要的识别特征
4. **生产友好**：可直接用于后续分镜参考

## 后续优化

1. 支持批量生成所有角色的设计图
2. 建立角色设计图库，支持版本对比
3. 与分镜生成功能联动，自动引用设计图作为参考
