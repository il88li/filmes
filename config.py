def init_default_channels():
    """تعيين القنوات الافتراضية إذا لم تكن موجودة"""
    from config import DEFAULT_SERIES_CHANNEL, DEFAULT_MOVIES_CHANNEL, DEFAULT_RECOMMENDATIONS_CHANNEL
    
    if not get_channel('series_channel'):
        set_channel('series_channel', DEFAULT_SERIES_CHANNEL)
        print(f"✅ تم تعيين قناة المسلسلات الافتراضية: {DEFAULT_SERIES_CHANNEL}")
    
    if not get_channel('movies_channel'):
        set_channel('movies_channel', DEFAULT_MOVIES_CHANNEL)
        print(f"✅ تم تعيين قناة الأفلام الافتراضية: {DEFAULT_MOVIES_CHANNEL}")
    
    if not get_channel('recommendations_channel'):
        set_recommendations_channel(DEFAULT_RECOMMENDATIONS_CHANNEL)
        print(f"✅ تم تعيين قناة التوصيات الافتراضية: {DEFAULT_RECOMMENDATIONS_CHANNEL}")
