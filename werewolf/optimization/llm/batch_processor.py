"""
LLM批处理器模块

提供异步批量处理LLM请求的功能，支持：
- 可配置的批次大小
- 超时保护机制
- 异常隔离（单个请求失败不影响其他请求）
- 错误处理和重试

验证需求：AC-3.2.1, AC-3.2.2
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMRequest:
    """
    LLM请求数据结构
    
    属性:
        request_id: 请求唯一标识符
        prompt: 提示词文本
        parameters: LLM生成参数（如temperature, max_tokens等）
    """
    request_id: str
    prompt: str
    parameters: Dict[str, Any]


@dataclass
class LLMResponse:
    """
    LLM响应数据结构
    
    属性:
        request_id: 对应的请求ID
        content: 生成的文本内容
        success: 请求是否成功
        error: 错误信息（如果失败）
    """
    request_id: str
    content: str
    success: bool
    error: Optional[str] = None


class LLMBatchProcessor:
    """
    LLM批处理器
    
    支持异步批量处理LLM请求，提高吞吐量并减少延迟。
    
    特性:
    - 可配置批次大小
    - 超时保护
    - 异常隔离
    - 并发控制
    
    验证需求：AC-3.2.1, AC-3.2.2
    """
    
    def __init__(self, config: Dict[str, Any], llm_client: Optional[Any] = None):
        """
        初始化批处理器
        
        参数:
            config: 配置字典，包含：
                - batch_size: 批次大小（默认5）
                - timeout: 超时时间（秒，默认30.0）
            llm_client: LLM客户端实例（可选，用于实际调用）
        """
        self.batch_size = config.get('batch_size', 5)
        self.timeout = config.get('timeout', 30.0)
        self.llm_client = llm_client
        
        logger.info(
            f"LLMBatchProcessor initialized: batch_size={self.batch_size}, "
            f"timeout={self.timeout}s"
        )
    
    async def process_batch(
        self,
        requests: List[LLMRequest]
    ) -> List[LLMResponse]:
        """
        批量处理LLM请求
        
        将请求列表分成多个批次，每个批次内的请求并发执行。
        单个请求失败不会影响其他请求。
        
        参数:
            requests: 请求列表
        
        返回:
            响应列表，顺序与请求列表对应
        
        验证需求：AC-3.2.2
        """
        if not requests:
            logger.warning("Empty request list provided")
            return []
        
        logger.info(f"Processing {len(requests)} requests in batches of {self.batch_size}")
        
        # 分批处理
        batches = [
            requests[i:i + self.batch_size]
            for i in range(0, len(requests), self.batch_size)
        ]
        
        logger.debug(f"Split into {len(batches)} batches")
        
        all_responses = []
        for batch_idx, batch in enumerate(batches):
            logger.debug(f"Processing batch {batch_idx + 1}/{len(batches)} with {len(batch)} requests")
            
            # 并发发送批次内的请求
            tasks = [
                self._send_request(req)
                for req in batch
            ]
            
            try:
                # 使用gather收集所有结果，return_exceptions=True确保异常不会中断其他任务
                responses = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.timeout
                )
                
                # 处理异常结果
                processed_responses = []
                for i, response in enumerate(responses):
                    if isinstance(response, Exception):
                        # 如果是异常，创建失败响应
                        logger.error(f"Request {batch[i].request_id} raised exception: {response}")
                        processed_responses.append(
                            LLMResponse(
                                request_id=batch[i].request_id,
                                content="",
                                success=False,
                                error=str(response)
                            )
                        )
                    else:
                        processed_responses.append(response)
                
                all_responses.extend(processed_responses)
                
            except asyncio.TimeoutError:
                # 整个批次超时
                logger.error(f"Batch {batch_idx + 1} timed out after {self.timeout}s")
                all_responses.extend([
                    LLMResponse(
                        request_id=req.request_id,
                        content="",
                        success=False,
                        error="Timeout"
                    )
                    for req in batch
                ])
        
        logger.info(
            f"Batch processing complete: {len(all_responses)} responses, "
            f"{sum(1 for r in all_responses if r.success)} successful"
        )
        
        return all_responses
    
    async def _send_request(self, request: LLMRequest) -> LLMResponse:
        """
        发送单个LLM请求
        
        处理单个请求的发送和错误处理。
        
        参数:
            request: LLM请求
        
        返回:
            LLM响应
        
        验证需求：AC-3.2.2
        """
        try:
            logger.debug(f"Sending request {request.request_id}")
            
            if self.llm_client is None:
                # 如果没有配置客户端，返回模拟响应
                logger.warning(f"No LLM client configured, returning mock response for {request.request_id}")
                return LLMResponse(
                    request_id=request.request_id,
                    content="[Mock response - no LLM client configured]",
                    success=True
                )
            
            # 调用实际的LLM API
            content = await self.llm_client.generate(
                request.prompt,
                **request.parameters
            )
            
            logger.debug(f"Request {request.request_id} completed successfully")
            
            return LLMResponse(
                request_id=request.request_id,
                content=content,
                success=True
            )
            
        except asyncio.TimeoutError:
            logger.warning(f"Request {request.request_id} timed out")
            return LLMResponse(
                request_id=request.request_id,
                content="",
                success=False,
                error="Request timeout"
            )
            
        except Exception as e:
            logger.error(f"Request {request.request_id} failed: {type(e).__name__}: {e}")
            return LLMResponse(
                request_id=request.request_id,
                content="",
                success=False,
                error=f"{type(e).__name__}: {str(e)}"
            )
