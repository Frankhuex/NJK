select distinct m.message_id from message m 
join msg_word mw on m.message_id=mw.message_id 
join word w on mw.word_id=w.id 
where (w.name='你居垦' and m.text not like '%你居垦%'
    or (w.name='爷爷' and m.text not like '%爷爷%')
);