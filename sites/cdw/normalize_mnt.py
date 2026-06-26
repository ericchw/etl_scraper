"""CDW → internal for monitors (product_code MNT)."""

from __future__ import annotations

import re

from core.schema.registry import empty_internal
from core.spec_lookup import extract_number, resolve_spec_field, spec_value, spec_list, split_and_filter_patterns, match_any
from core.units import length_to_in, weight_to_lb
from sites.cdw._common import cdw_payload, fill_identity_content, fill_item_dimensions_weight, parse_inch, to_int_number
from sites.cdw.spec_bindings import CDW_PROCESSOR_BINDINGS

def normalize_cdw_mnt(raw: dict) -> dict:
    cdw = cdw_payload(raw)
    specs = cdw.get("specs") or {}
    internal = empty_internal("MNT")

    fill_identity_content(internal, raw=raw, cdw=cdw, specs=specs, spec_value=spec_value)

    # identity and content dict get from cdw\_common fill_identity_content()

    # display
    internal["display"]["size_in"] = extract_number(spec_value(specs, "Display & Graphics", "Screen Size"))
    internal["display"]["panel"] = spec_value(specs, "Display & Graphics", "TFT Technology") or spec_value(specs, "Display & Graphics", "Display Screen Technology")
    internal["display"]["backlight_technology"] = spec_value(specs, "Display & Graphics", "Display Backlight Technology")
    internal["display"]["resolution"] = (spec_value(specs, "Display & Graphics", "Native Resolution") or spec_value(specs, "Video", "Max Video Resolution"))
    internal["display"]["video_format"] = spec_value(specs, "Display & Graphics", "Video Format") or spec_value(specs,"Display & Graphics", "Video Format (Non-standard)")
    internal["display"]["features"] = spec_list(specs, "Display & Graphics", "Features")
    internal["display"]["color_support"] = to_int_number(spec_value(specs, "Display & Graphics", "Color Support"))
    internal["display"]["brightness_cdm2"] = extract_number(spec_value(specs, "Display & Graphics", "Display Image Brightness"))
    internal["display"]["refresh_rate_hz"] = extract_number(spec_value(specs, "Display & Graphics", "V-Sync Rate at Max Res."))
    internal["display"]["response_time"] = spec_list(specs, "Display & Graphics", "Typical Response Time")
    internal["display"]["aspect_ratio"] = spec_value(specs, "Display & Graphics", "Monitor Aspect Ratio")
    internal["display"]["static_contrast_ratio"] = spec_value(specs, "Display & Graphics", "Display Contrast Ratio")
    internal["display"]["adjustment"]["height"] = match_any(spec_value(specs, "Display & Graphics", "Display Position Adjustments"), ["height"])
    internal["display"]["adjustment"]["pivot"] = match_any(spec_value(specs, "Display & Graphics", "Display Position Adjustments"), ["pivot", "rotation"])
    internal["display"]["adjustment"]["swivel"] = match_any(spec_value(specs, "Display & Graphics", "Display Position Adjustments"), ["swivel"])
    internal["display"]["adjustment"]["tilt"] = match_any(spec_value(specs, "Display & Graphics", "Display Position Adjustments"), ["tilt"])
    internal["display"]["adjustment_scale"]["height_mm"] = spec_value(specs, "Display & Graphics", "Height Adjustment")
    internal["display"]["adjustment_scale"]["rotation_angle"] = spec_value(specs, "Display & Graphics", "Rotation Angle")
    internal["display"]["adjustment_scale"]["swivel_angle"] = spec_value(specs, "Display & Graphics", "Swivel Angle")
    internal["display"]["adjustment_scale"]["tilt_angle"] = spec_value(specs, "Display & Graphics", "Tilt Angle")
    internal["display"]["screen_coating"] = spec_list(specs, "Display & Graphics", "Display Screen Coating")
    internal["display"]["screen_technology"] = spec_list(specs, "Display & Graphics", "Display Screen Technology")
    internal["display"]["display_type"] = spec_value(specs, "Display & Graphics", "Display Type").replace(" monitor", "") or spec_value(specs, "Display & Graphics", "Panel Type")
    internal["display"]["form_factor"] = spec_value(specs, "Display & Graphics", "Form Factor")
    internal["display"]["hdr"]["hdr_capable"] = spec_value(specs, "Display & Graphics", "HDR Capable")
    internal["display"]["hdr"]["hdr_format"] = spec_value(specs, "Display & Graphics", "HDR Format")
    internal["display"]["horizonal_refresh_rate"] = spec_value(specs, "Display & Graphics", "Horizontal Refresh Rate")
    internal["display"]["vertical_refresh_rate"] = spec_value(specs, "Display & Graphics", "Vertical Refresh Rate")
    internal["display"]["horizontal_viewing_angle"] = spec_value(specs, "Display & Graphics","Horizontal Viewing Angle")
    internal["display"]["vertical_viewing_angle"] = spec_value(specs, "Display & Graphics","Vertical Viewing Angle")
    internal["display"]["pixel_density_ppl"] = extract_number(spec_value(specs, "Display & Graphics", "Pixel Density (ppi)"))
    internal["display"]["pixel_pitch_mm"] = extract_number(spec_value(specs, "Display & Graphics", "Pixel Pitch"))
    internal["display"]["widescreen"] = match_any(spec_value(specs, "Display & Graphics", "Widescreen Display"), ["yes"])
    internal["display"]["curve_screen"] = match_any(spec_value(specs, "Display & Graphics", "Curved Screen"), ["yes"])
    internal["display"]["screen_curvature"] = spec_value(specs, "Display & Graphics", "Screen Curvature")
    internal["display"]["touchscreen"] = match_any(spec_value(specs, "Display & Graphics", "Touchscreen"), ["yes"])
    internal["display"]["color_gamut"] = spec_list(specs, "Video", "Color Gamut")

    # audio
    internal["audio"]["speaker"] = match_any(spec_value(specs, "Audio", "Speakers Configuration"), ["*"])
    internal["audio"]["output_type"] = spec_value(specs, "Audio", "Output Type")
    internal["audio"]["speaker_output_power_watt"] = extract_number(spec_value(specs, "Audio", "Speaker Output Power"))
    internal["audio"]["speaker_configuration"] = spec_value(specs, "Audio", "Speakers Configuration")

    # camera
    internal["camera"]["webcam"] = match_any(spec_value(specs, "Product Information", "Built-in Camera"), ["yes"])

    # io
    internal["io"]["output_type"] = spec_list(specs, "Display & Graphics", "Input Signal")
    internal["io"]["interfaces"] = spec_list(specs, "Connectivity", "Interfaces")
    internal["io"]["usb_hub"] = match_any(spec_value(specs, "Product Information", "Built-in USB Hub"), ["yes"])
    internal["io"]["usb_power_delivery_watt"] = spec_value(specs, "Product Information", "USB Power Delivery").replace(" watt", "")
    internal["io"]["built-in_devices"] = spec_list(specs, "Technical Information", "Built-in Devices")

    # power
    internal["power"]["energy_class"] = spec_value(specs, "Power", "Energy Class").replace("Class ","")
    internal["power"]["frequency_hz"] = spec_value(specs, "Power", "Frequency").replace(" hertz", "")
    internal["power"]["consumption_watt"]["off_mode"]= spec_value(specs, "Power", "Power Consumption (Off Mode)").replace(" watt", "")
    internal["power"]["consumption_watt"]["on_mode"] = spec_value(specs, "Power","Power Consumption (On Mode)").replace(" watt", "")
    internal["power"]["consumption_watt"]["typical"] = spec_value(specs, "Power","Power Consumption (Typical)").replace(" watt", "")
    internal["power"]["consumption_watt"]["max"] = spec_value(specs, "Technical Information", "Max Power Consumption").replace(" watt","")
    internal["power"]["consumption_watt"]["standby"] = spec_value(specs, "Energy & Performance", "Standby Power Consumption").replace(" watt","")
    internal["power"]["voltage_required"] = spec_value(specs, "Power", "Required Voltage").replace("AC ", "").replace(" watt", "")

    # software
    internal["software"]["types"] = spec_list(specs, "Software", "Software Type")
    internal["software"]["operating_system_required"] = spec_list(specs, "Technical Information", "Operating System Required")

    # technical
    internal["technical"]["max_operating_temperature_degree"] = extract_number(spec_value(specs, "Technical Information", "Max Operating Temperature"))
    internal["technical"]["min_operating_temperature_degree"] = extract_number(spec_value(specs, "Technical Information", "Min Operating Temperature"))
    internal["technical"]["operating_humidity"] = spec_value(specs, "Technical Information", "Operating Humidity")
    internal["technical"]["features"] = spec_list(specs, "Technical Information", "Features")
    # internal["technical"]["mount_size"] = spec_list(specs, "Product Information", "Flat Panel Mount Interface").replace(" mm","")
    internal["technical"]["vesa_mount"] = match_any(spec_value(specs, "Product Information", "Flat Panel Mount Interface"), ["*"])
    internal["technical"]["vesa_mount_size"] = [s.replace(" mm", "") for s in spec_list(specs, "Product Information", "Flat Panel Mount Interface")]
    internal["technical"]["security_slot_type"] = spec_value(specs, "Product Information", "Security Slot Type")
    internal["technical"]["tv_tuner_presence"] = match_any(spec_value(specs, "Product Information", "TV Tuner Presence"), ["yes"])

    # certification
    internal["certification"]["compliant_standards"] = spec_list(specs, "Certifications & Listings", "Compliant Standards")
    internal["certification"]["energy_star_certified"] = match_any(spec_value(specs, "Certifications & Listings", "ENERGY STAR Certified"), ["yes"])
    internal["certification"]["energy_star_version"] = spec_value(specs, "Certifications & Listings", "Energy Star Version")
    internal["certification"]["epeat_compliant"] = match_any(spec_value(specs, "Certifications & Listings", "EPEAT Compliant"), ["yes"])
    internal["certification"]["epeat_level"] = spec_value(specs, "Certifications & Listings", "EPEAT Level").replace(" ", "").replace("EPEAT", "")
    internal["certification"]["tco_certified"] = match_any(spec_value(specs, "Certifications & Listings", "TCO Certified") , ["yes"])
    internal["certification"]["environmental_certification"] = spec_list(specs, "Certifications & Listings", "Environmental Certification")
    internal["certification"]["hdr_certification"] = spec_value(specs, "Display & Graphics","HDR Certification")
    internal["certification"]["software_certification"] = spec_list(specs, "Software", "Software Certification")

    # included_items
    acc = spec_value(specs, "Included Items", "Cables")
    if acc: internal["included_items"] = [p.strip() for p in re.split(r"[,;]", acc) if p.strip()]

    # physical
    internal["physical"]["packaged_qty"] = spec_value(specs, "Product Information", "Packaged Quantity")
    internal["physical"]["color"] = spec_value(specs, "Physical Characteristics", "Color")
    internal["physical"]["color_category"] = spec_value(specs, "Physical Characteristics", "Color Category")
    fill_item_dimensions_weight(internal,specs, spec_value=spec_value, length_to_in=length_to_in, weight_to_lb=weight_to_lb,)

    return internal
