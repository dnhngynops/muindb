#!/usr/bin/env python3
"""
Phase 4 Database Models for Producer Management Tracking
Billboard Music Database - Producer Management and A&R Insights
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, Date, DateTime, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class ManagementCompany(Base):
    """Management companies, record labels, and publishers"""
    __tablename__ = 'management_companies'
    
    company_id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(255), nullable=False, unique=True)
    company_type = Column(String(50), nullable=False)  # 'management', 'label', 'publisher', 'agency'
    website = Column(String(500))
    headquarters = Column(String(255))
    founded_year = Column(Integer)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    producer_management = relationship("ProducerManagement", back_populates="company")
    management_effectiveness = relationship("ManagementEffectiveness", back_populates="company")

class ProducerManagement(Base):
    """Tracks which producers are under management"""
    __tablename__ = 'producer_management'
    
    management_id = Column(Integer, primary_key=True, autoincrement=True)
    producer_id = Column(Integer, ForeignKey('credits.credit_id', ondelete='CASCADE'), nullable=False)
    company_id = Column(Integer, ForeignKey('management_companies.company_id', ondelete='CASCADE'), nullable=False)
    management_type = Column(String(50), nullable=False)  # 'exclusive', 'non-exclusive', 'former'
    start_date = Column(Date)
    end_date = Column(Date)
    is_current = Column(Boolean, default=True)
    notes = Column(Text)
    source = Column(String(100), default='manual')  # 'manual', 'api', 'web_scrape'
    confidence_score = Column(Numeric(3, 2), default=1.0)  # 0.0 to 1.0
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    producer = relationship("Credits")
    company = relationship("ManagementCompany", back_populates="producer_management")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('producer_id', 'company_id', 'management_type', name='uq_producer_company_type'),
    )

class ManagementVerification(Base):
    """Tracks verification attempts and results"""
    __tablename__ = 'management_verification'
    
    verification_id = Column(Integer, primary_key=True, autoincrement=True)
    producer_id = Column(Integer, ForeignKey('credits.credit_id', ondelete='CASCADE'), nullable=False)
    company_id = Column(Integer, ForeignKey('management_companies.company_id', ondelete='CASCADE'))
    verification_methods = Column(Text)  # JSON array of methods: ['api', 'web_scrape', 'manual', 'social_media']
    verification_status = Column(String(20), nullable=False)  # 'verified', 'unverified', 'disputed', 'pending'
    verification_date = Column(DateTime, default=datetime.utcnow)
    verification_notes = Column(Text)  # JSON array of notes
    source_urls = Column(Text)  # JSON array of URLs
    confidence_score = Column(Numeric(3, 2), default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    producer = relationship("Credits")
    company = relationship("ManagementCompany")

class ProducerPerformanceMetrics(Base):
    """Tracks producer success metrics"""
    __tablename__ = 'producer_performance_metrics'
    
    metric_id = Column(Integer, primary_key=True, autoincrement=True)
    producer_id = Column(Integer, ForeignKey('credits.credit_id', ondelete='CASCADE'), nullable=False)
    year = Column(Integer)
    total_songs = Column(Integer, default=0)
    number_one_hits = Column(Integer, default=0)
    top_10_hits = Column(Integer, default=0)
    top_40_hits = Column(Integer, default=0)
    total_weeks_on_chart = Column(Integer, default=0)
    average_peak_position = Column(Numeric(5, 2))
    success_rate = Column(Numeric(5, 2))  # percentage of songs that charted
    genre_diversity_score = Column(Numeric(3, 2))  # how many different genres they work in
    collaboration_count = Column(Integer, default=0)  # how many different artists they work with
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    producer = relationship("Credits")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('producer_id', 'year', name='uq_producer_year_metrics'),
    )

class ManagementEffectiveness(Base):
    """Tracks how effective different management companies are"""
    __tablename__ = 'management_effectiveness'
    
    effectiveness_id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('management_companies.company_id', ondelete='CASCADE'), nullable=False)
    year = Column(Integer)
    total_producers = Column(Integer, default=0)
    active_producers = Column(Integer, default=0)
    total_hits = Column(Integer, default=0)
    number_one_hits = Column(Integer, default=0)
    average_success_rate = Column(Numeric(5, 2))
    top_producer_id = Column(Integer, ForeignKey('credits.credit_id', ondelete='CASCADE'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("ManagementCompany", back_populates="management_effectiveness")
    top_producer = relationship("Credits")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('company_id', 'year', name='uq_company_year_effectiveness'),
    )

# Import the Credits model from phase2_models to establish relationships
try:
    from database.phase2_models import Credits
except ImportError:
    # If phase2_models is not available, define a placeholder
    class Credits:
        pass
