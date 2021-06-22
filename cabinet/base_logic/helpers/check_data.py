def check_in_regions(inn, regions, kpp=None) -> bool:
    inns = [str(inn)[:2], str(inn)[:3]]
    if kpp:
        inns.append(str(kpp)[:2])
        inns.append(str(kpp)[:3])
    find = False
    for inn in inns:
        if inn in regions:
            find = True
            break
    return find
