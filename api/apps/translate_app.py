#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import os
import logging
from flask import request
from transformers import T5ForConditionalGeneration, T5Tokenizer
import torch

from api.utils.api_utils import get_json_result, server_error_response, validate_request

# 全局变量存储模型和分词器
model = None
tokenizer = None
device = "cpu"  # 或 'cuda' 如果有GPU

def load_translation_model():
    """加载T5翻译模型"""
    global model, tokenizer
    
    if model is not None and tokenizer is not None:
        return True
        
    try:
        model_name = "utrobinmv/t5_translate_en_ru_zh_small_1024"
        MODEL_PATH = "./models"
        
        # 尝试从本地路径加载模型
        if os.path.exists(MODEL_PATH):
            logging.info(f"Loading T5 model from local path: {MODEL_PATH}")
            model = T5ForConditionalGeneration.from_pretrained(MODEL_PATH)
            tokenizer = T5Tokenizer.from_pretrained(MODEL_PATH)
        else:
            # 从Hugging Face加载模型
            logging.info(f"Loading T5 model from Hugging Face: {model_name}")
            model = T5ForConditionalGeneration.from_pretrained(model_name)
            tokenizer = T5Tokenizer.from_pretrained(model_name)
        
        model.to(device)
        logging.info("T5 translation model loaded successfully")
        return True
        
    except Exception as e:
        logging.error(f"Failed to load T5 translation model: {e}")
        return False

def translate_text(text, source_lang="zh", target_lang="en"):
    """翻译文本"""
    global model, tokenizer
    
    if model is None or tokenizer is None:
        if not load_translation_model():
            raise Exception("Translation model not available")
    
    try:
        # 根据目标语言设置前缀
        if target_lang == "en":
            prefix = "translate to en: "
        elif target_lang == "zh":
            prefix = "translate to zh: "
        else:
            prefix = f"translate to {target_lang}: "
        
        src_text = prefix + text
        
        # 编码输入
        input_ids = tokenizer(src_text, return_tensors="pt", max_length=512, truncation=True)
        
        # 生成翻译
        with torch.no_grad():
            generated_tokens = model.generate(
                **input_ids.to(device),
                max_length=512,
                num_beams=4,
                early_stopping=True,
                do_sample=False
            )
        
        # 解码结果
        result = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
        translated_text = result[0] if result else text
        
        return translated_text
        
    except Exception as e:
        logging.error(f"Translation failed: {e}")
        return text  # 翻译失败时返回原文


@manager.route("/translate", methods=["POST"])  # noqa: F821
@validate_request("text")
def translate():
    """
    翻译API端点
    ---
    tags:
      - Translation
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            text:
              type: string
              description: 要翻译的文本
              example: "你好世界"
            source_lang:
              type: string
              description: 源语言代码
              default: "zh"
              example: "zh"
            target_lang:
              type: string
              description: 目标语言代码
              default: "en"
              example: "en"
    responses:
      200:
        description: 翻译成功
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 0
            message:
              type: string
              example: "success"
            data:
              type: object
              properties:
                original_text:
                  type: string
                  example: "你好世界"
                translated_text:
                  type: string
                  example: "Hello world"
                source_lang:
                  type: string
                  example: "zh"
                target_lang:
                  type: string
                  example: "en"
      400:
        description: 请求参数错误
      500:
        description: 服务器内部错误
    """
    try:
        req = request.json
        text = req.get("text", "").strip()
        source_lang = req.get("source_lang", "zh")
        target_lang = req.get("target_lang", "en")
        
        if not text:
            return get_json_result(
                data=False, 
                message="Text is required", 
                code=400
            )
        
        # 执行翻译
        translated_text = translate_text(text, source_lang, target_lang)
        
        result = {
            "original_text": text,
            "translated_text": translated_text,
            "source_lang": source_lang,
            "target_lang": target_lang
        }
        
        return get_json_result(data=result, message="Translation successful")
        
    except Exception as e:
        logging.error(f"Translation API error: {e}")
        return server_error_response(e)


@manager.route("/translate/health", methods=["GET"])  # noqa: F821
def translate_health():
    """
    翻译服务健康检查
    ---
    tags:
      - Translation
    responses:
      200:
        description: 服务正常
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 0
            message:
              type: string
              example: "Translation service is healthy"
            data:
              type: object
              properties:
                model_loaded:
                  type: boolean
                  example: true
                device:
                  type: string
                  example: "cpu"
    """
    try:
        global model, tokenizer
        
        model_loaded = model is not None and tokenizer is not None
        
        if not model_loaded:
            # 尝试加载模型
            model_loaded = load_translation_model()
        
        result = {
            "model_loaded": model_loaded,
            "device": device
        }
        
        return get_json_result(
            data=result, 
            message="Translation service is healthy" if model_loaded else "Translation model not loaded"
        )
        
    except Exception as e:
        logging.error(f"Translation health check error: {e}")
        return server_error_response(e)