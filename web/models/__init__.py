"""
数据模型模块
"""
from web.models.user_model import UserModel, VerificationCodeModel, user_model, verification_model
from web.models.point_model import PointModel, point_model

__all__ = ['UserModel', 'VerificationCodeModel', 'user_model', 'verification_model', 
           'PointModel', 'point_model']